# Audit 04: the core "spec" skill family (ponytail lens)

The review tree is `review-v13` at `0acbd06` (tip of `gsd/v1.3-curated-config-v2`). Every path below is relative to `skills/` unless it is marked otherwise. The method follows `ponytail:ponytail-audit` and `ponytail:ponytail-review`: correct, safe, holds under load, tested, fast, lean. No file in any repo was edited. No live reviewer or executor dispatch was run.

**What this repo does:** ai-kit ships agent skills for spec review and plan execution across five AI CLIs:
- `ai-kit-spec-review` runs a review-and-fix loop. The reviewer can be native or another AI CLI, chosen from a quota-checked "ladder" in `review-spec.toml`.
- `ai-kit-spec-execute*` sends a GSD phase or a superpowers plan task to a chosen model or CLI.
- `ai-kit-spec-config` writes the config.

**Load assumed:** one developer on one machine, with sometimes two agent sessions at once. Every input is the user's own, so it is trusted but can be malformed: paths, config, and plan files.

**Verification baseline (VERIFIED):** `uv run python -m unittest tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers tests.test_ai_kit_rules_common` gave `Ran 904 tests in 0.650s, OK`. The tests pass, but none of them exercises the bugs below.

Confidence key:
- **VERIFIED:** reproduced by a command shown here.
- **READ:** confirmed by reading the code at the cited lines.
- **INFERENCE:** reasoned, not run.

---

## Must fix

### 1. A failed reviewer merges into "Approved" (VERIFIED)
**Where:** `ai-kit-spec-review/ai_kit_spec/review_reports.py:16-37,139`, `ai-kit-spec-review/SKILL.md:413`, `ai-kit-spec-review-checklist/SKILL.md:29`, `ai-kit-spec-review-fixer/SKILL.md:20`

- **What this is:** In "double" mode, two reviewers' reports are merged. The merged `### Status:` line decides whether the loop ends.
- **Problem:** The checklist skill can emit `### Status: Failure — input not on disk…`. `report_has_status` only checks that the substring `### Status:` exists, so a Failure report passes as "readable". It has no findings, so the merge prints `### Status: Approved`.
  - Reproduced: `merge-reports a=<Approved report> b=<Failure report>` printed `### Status: Approved`.
  - Single mode has the same root cause in a different form. The orchestrator table (`SKILL.md:413`) says "any other text → treat as Issues Found", so a Failure from the reviewer sends the fixer off with no findings to fix.
  - The fixer's own `Failure` status is missing from the Step 4 table entirely.
- **Fix:** Use one closed status vocabulary. In `review_reports.py`, accept only `Approved` or `Issues Found` as a valid status, so `report_has_status` returns False for anything else. In `SKILL.md` Step 2 and Step 4, add a `Failure` row that goes to Surface failure. About 5 lines plus 1 test.
- **If we skip it:** A review where one reviewer never read the document is reported as approved.

### 2. Claude and grok execute commands break on any path with a space or a quote; a `;` in a directory name runs a second command (VERIFIED)
**Where:** `ai-kit-spec-review/ai_kit_spec/commands.py:141-148,202-204,224-226`

- **What this is:** These builders make the shell command that runs a write-capable CLI inside `target_dir`.
- **Problem:** `_require_target_dir` returns `shlex.quote(dir)`, which adds single quotes. That value is then pasted inside an outer `sh -c '…'` single-quoted string, so the inner quotes close the outer ones.
  - Reproduced with `target_dir=".../probe/My Proj"`: `sh: cd: .../probe/My: No such file or directory`.
  - With `My Proj;echo PWNED`, the `;` lands outside any quotes in the outer shell.
  - Codex is fine because it has no `sh -c` wrapper.
  - The only quoting test covers codex alone (`tests/test_ai_kit_spec.py:3587-3589`).
  - The superpowers `dispatch-task` path and the GSD wrapper both reach these builders through `dispatch_execute`.
- **Fix:** Quote the inner script once as a whole, for example `"sh -c " + shlex.quote(f"cd {shlex.quote(d)} && exec claude … --model {{model}} …")`. Do the same for grok. Add one test per CLI with `"/tmp/a b"`.
- **If we skip it:** Any project under a folder with a space (common on macOS) cannot run claude or grok execution. A crafted directory name can inject a command.

### 3. The GSD execute path ignores `purpose` and silently drops `effort`/`service_tier` (VERIFIED)
**Where:** `ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py:32-52`, `ai-kit-spec-execute-gsd/SKILL.md:152`

- **What this is:** This code turns the user's `[[reviewers]]` entries into execute candidates for GSD.
- **Problem:** The GSD `assemble_candidates` copies 8 fields, but not `purpose`, `effort` or `service_tier`. The superpowers copy of the same function does copy them (`dispatch_injection.py:153-159`).
  - Reproduced with ladder `[rev(purpose=review, effort=high), exe(purpose=execute)]`. GSD picked `rev`, the review-only entry, and built `codex exec … -m gpt-5.6` with no `-c model_reasoning_effort`. Superpowers picked `exe`.
  - Even when the candidate does carry effort, the `WRAPPER_COMMAND` that GSD actually stores passes only `--cli --model` (`SKILL.md:152`). That drops effort a second time.
  - The comment at `gsd_cross_ai.py:27-30` says this exact gap was "fixed 2026-08-31". It is still there.
  - `tests/test_ai_kit_spec_gsd.py:812-838` pins the purpose-blindness as a "load-bearing coincidence". Purpose-blindness may therefore be intended, but dropping effort is not.
- **Fix:** Keep one `assemble_candidates` in `ai_kit_spec/execute_selection.py` that copies all fields, and import it from both adapters. Return `effort`/`service_tier` in the `resolve-dispatch` JSON, and add `--effort`/`--service-tier` to `WRAPPER_COMMAND`. Net effect: delete about 20 lines, add about 4.
- **If we skip it:** GSD runs use review-only models for coding, at default effort, while the config says otherwise.

### 4. The superpowers flow passes the whole CLI transcript as one command-line argument and echoes it into the agent context (VERIFIED)
**Where:** `ai-kit-spec-execute-superpowers/SKILL.md:334-338,357`, `ai_kit_spec_superpowers/cli.py:328-331`

- **What this is:** After each task dispatch, the result JSON (the CLI's full stdout and stderr) goes into a shell variable. It is printed with `printf`, then passed as `--dispatch-result-json "$X"`.
- **Problem:** Linux caps a single argv string at 128 KiB. Reproduced: a 140 KB argument raised `[Errno 7] Argument list too long`. A long codex or opencode run easily writes more than that to stderr, and then `classify-dispatch-failure` cannot run. The `printf` also pastes the whole transcript into the orchestrator's context on every task.
- **Fix:** Have `dispatch-task` write the result to `$RUN_DIR/task-N-result.json` and print only the path plus `returncode`/`timed_out`. Have `classify-dispatch-failure` take `--dispatch-result-path`. Also drop the `printf`.
- **If we skip it:** Long tasks crash the classify step, and every task spends thousands of tokens on transcript echo.

---

## Should fix

### 5. Any output that mentions "quota" is classified as a quota failure, and the task is retried on another CLI over a half-edited tree (VERIFIED)
**Where:** `ai_kit_spec_superpowers/dispatch_injection.py:25,360-379`

- **What this is:** This code decides whether a failed task means "out of quota, try the next CLI" or "real failure, block".
- **Problem:** It does a substring match of `"quota"` over the combined stdout and stderr. Reproduced: `{'returncode': 1, 'stdout': 'Modified skills/ai_kit_spec/quota.py; 2 tests failed'}` returned `quota`. In this very repo, any task that touches `quota.py` and fails is re-run by a different CLI on top of the first CLI's partial edits.
- **Fix:** Match only real limit phrases such as `usage limit`, `rate limit`, `quota exceeded` or `exceeded your`, and only in stderr. One-line change plus one test.
- **If we skip it:** Real failures turn into silent re-runs by another model on a dirty worktree.

### 6. The codegraph health check has no timeout, and its auto-install changes the user's global CLI configs without asking (READ)
**Where:** `ai-kit-spec-review/ai_kit_spec/detection.py:542-577,602-613`, duplicated in `ai_kit_spec_gsd/cli.py:185-195` and `ai_kit_spec_superpowers/cli.py:285-293`

- **What this is:** Before every reviewer or executor dispatch, the code runs `claude mcp get/list` (or the codex, cursor or opencode equivalent). If codegraph is missing, it runs `codegraph install --target=<cli> --location=global --yes --init`.
- **Problem:**
  - None of those three `run_fn` calls has a `timeout`. `claude mcp list` connects to every MCP server, so one hung server blocks `dispatch-reviewer` forever.
  - The install writes the global MCP config of claude, codex, cursor or opencode with `--yes`. No SKILL.md tells the user this happens: `ai-kit-spec-execute-gsd/SKILL.md:221` only names the function.
- **Fix:**
  - Add `timeout=15` to all three calls and treat a timeout as "not healthy".
  - Make the install opt-in, or at least announce it in the SKILL text.
  - Move the duplicated "ensure, then index with a 15s timeout" block from both adapter CLIs into one `detection.prepare_codegraph(cli, target_dir)`.
- **If we skip it:** Dispatches can hang. Users find codegraph registered in their CLIs without having agreed to it.

### 7. A typo in `review-spec.toml` silently turns cross-AI review off (READ)
**Where:** `ai-kit-spec-review/ai_kit_spec/config_io.py:27-39,85-93`

- **What this is:** These are the reader and the hand-rolled writer for the reviewer config.
- **Problem:**
  - `cfg_load_toml` returns `{}` on a `TOMLDecodeError` and prints nothing. A missing quote in a hand-edited local file makes `cfg_resolve` fall back to global or to no reviewers, and the review quietly runs native-only.
  - The writer escapes only `\` and `"`. A newline or control character in a value (for example a multi-line `command`) produces TOML that the reader then drops without a word.
- **Fix:** On a decode error, print `WARNING: <path> is not valid TOML: <err>` to stderr. In `_toml_value`, escape `\n`, `\t` and other control characters (or reject them). About 4 lines.
- **If we skip it:** "Why did my cross-AI reviewer stop running?" has no visible answer.

### 8. The quota probe leaks child processes, misreads slow CLIs, and pays for probes the ladder never uses (READ for code; slowness is INFERENCE)
**Where:** `ai-kit-spec-review/ai_kit_spec/quota.py:237-243`, `ai_kit_spec_gsd/cli.py:132-139`

- **What this is:** The probe sends a real "Only say: Hello world!" prompt to each reviewer CLI and caches the result for 1 hour.
- **Problem:**
  - It uses `subprocess.run(shell=True, timeout=30)`. On timeout that kills only the direct child. The Node CLIs' worker processes keep running: the exact bug `dispatch.py:35-43` documents and fixes for dispatch.
  - A cold start over 30s marks the CLI unavailable for a full hour.
  - GSD's `resolve-dispatch` probes every `[[reviewers]]` entry, not just the ladder. Those are sequential, paid model calls.
- **Fix:** Run the probe through `dispatch.dispatch_with_heartbeat(cmd, prompt, 30, 30)`, which already kills the whole process group. Pass `top_n_keys` instead of every candidate key.
- **If we skip it:** Orphaned CLI processes pile up, good reviewers get skipped after a slow start, and probe calls are paid for nothing.

### 9. The "read-only reviewer" promise is not enforced for opencode and claude (READ; INFERENCE on opencode's default permissions)
**Where:** `ai-kit-spec-review/ai_kit_spec/commands.py:92-95,110-113`, `reviewer_dispatch.py:1-8`

- **What this is:** These are the review-mode command builders. The module docstring says the reviewer path is "read-only by construction".
- **Problem:**
  - Codex gets `--sandbox read-only` and cursor gets `--mode plan`.
  - `opencode run -m {model}` has no read-only flag.
  - `claude -p` inherits the user's permission mode, and this user runs bypass mode.
  - Neither CLI profile mentions this.
  - Result: a reviewer can edit the document under review, which breaks the reviewer/fixer separation the SKILL calls "audit integrity".
- **Fix:** Add `--permission-mode plan` to the claude review builder. Add opencode to a soft-confinement list for review, as `NO_HARD_SANDBOX_CLIS` already does for execute. Change the docstring so it no longer claims read-only by construction.
- **If we skip it:** Reviewer edits can slip into the document with no record.

### 10. GSD `.planning/` collects a new backup file on every run (READ)
**Where:** `ai_kit_spec_gsd/gsd_config.py:26,140-152`, `ai-kit-spec-execute-gsd/SKILL.md:146`

- **What this is:** This is the backup taken before each `config.json` write.
- **Problem:**
  - The backup name includes a millisecond run id, so 50 phase runs leave 50 `config.json.ai-kit-spec-execute-gsd.<ms>.bak` files.
  - No code removes them (only tests grep `.bak`).
  - The format-block file is also left in `.planning/`.
  - GSD commits `.planning/` docs (INFERENCE), so these files can end up in git.
- **Fix:** Use one fixed backup name, `config.json.ai-kit-spec-execute-gsd.bak`, overwritten on each run. One line.
- **If we skip it:** The planning directory clutters up and the noise may get committed.

### 11. A GSD cross-AI hook with whitespace in any path is written anyway, broken (READ)
**Where:** `ai-kit-spec-execute-gsd/SKILL.md:149-152`, `references/dispatch-notes.md:6-21`

- **What this is:** This is the `workflow.cross_ai_command` string that GSD later word-splits.
- **Problem:** The notes correctly say GSD's `${CROSS_AI_CMD}` cannot carry whitespace, but nothing guards it. A repo or `TOOLS_PY` path with a space is still written into the config, and the failure only appears when GSD runs it.
- **Fix:** In `resolve_gsd_dispatch`, return `fallback_notice(reason="path_has_whitespace")` when `target_dir` contains whitespace. The SKILL step does the same check for `$TOOLS_PY` and `$FORMAT_BLOCK_PATH`. About 3 lines.
- **If we skip it:** The failure is deferred and confusing, inside GSD's own retry UI.

### 12. Dead code (READ, each name checked by grep across skills/tests/docs)

- **What this is:** These are code paths that nothing runs:
  - `render-command` subcommand (`cli.py:754-760,1169-1186`): no SKILL or reference uses it, only old plans in `docs/`. Its sibling `reviewer_dispatch.py:110-114` calls exactly this pre-render pattern an injection hazard.
  - `prepare-cross-ai-guidance` (`ai_kit_spec_gsd/cli.py:107-111,201-203`) and `build_gsd_cross_ai_guidance` (`cross_ai_guidance.py:38-43`): replaced on 2026-08-30. Zero SKILL uses.
  - `_unimplemented_execute_command` (`commands.py:279-286`): never registered; it appears only in a docstring.
  - `dispatch.write_resumable_state` (`dispatch.py:201-206`): a one-line pass-through to `cache_write_json`.
  - The `affinity_table` parameter threaded through 4 functions: documented as unused (`execute_selection.py:37-43`).
  - The string returned by `build_cross_ai_command`: GSD stores `WRAPPER_COMMAND` instead (`SKILL.md:129-131`), so its only remaining job is a dispatchability yes/no.
- **Problem:** All of this has to be read, tested and kept in sync. `render-command` is also a footgun.
- **Fix:** Delete them along with their tests. Replace `build_cross_ai_command` with a `try: build_execute_command(…) except ValueError` check.
- **If we skip it:** About 120 lines of code plus about 60 lines of tests stay with no user.

### 13. Two dispatchers do one job (READ)
**Where:** `ai-kit-spec-review/ai_kit_spec/dispatch.py:46-98` vs `101-198`

- **What this is:** `dispatch_with_heartbeat` (pipes, used by execute) and `dispatch_with_polling` (files plus tiers, used by review).
- **Problem:** Both start a shell in its own session, enforce a timeout and kill the process group. The polling version is the safer design of the two: no pipes at all, and a progress report based on file size. Two versions means two sets of edge cases and two sets of tests.
- **Fix:** Have `dispatch_execute` call `dispatch_with_polling(cmd, prompt, [timeout], poll_interval=heartbeat_interval)` and delete `dispatch_with_heartbeat` with its tests. This also fixes #8 if the probe uses the same function.
- **If we skip it:** Each fix to timeout handling has to be made twice.

### 14. Copies that have already drifted (READ)

- **What this is:** Several pieces exist in two or more places:
  - `assemble_candidates` in both adapters (the root cause of #3).
  - The codegraph-prepare block (#6).
  - `_AUTH_SIGNALS`, marked "keep in sync by hand" (`dispatch_injection.py:26-31`), against `quota._UNAVAILABLE_SIGNALS`.
  - `_VALID_NATIVE_RUNTIME`, marked "must change together" (`config_io.py:97-100` against `model_catalog.py:53`).
  - The path-resolution shell block, copied into 5 SKILL docs: review (SEEDS_DIR), cross-ai-dispatch (TOOLS_PY), config, execute, superpowers. Each copy is 15 to 30 lines.
- **Problem:** #3 shows the drift is real, not theoretical.
- **Fix:** Make each one a single shared constant or function in `ai_kit_spec/`, and import it everywhere. For the path blocks: `ai-kit-spec.py` already knows its own directory, so add one `ai-kit-spec.py paths` subcommand that prints every path a skill needs, and each SKILL calls it with one line.

### 15. About 40% of the library is comments and docstrings, much of it review history (VERIFIED by tokenizer count)

- **What this is:** Comment and docstring lines per file in `ai_kit_spec/`:
  - `commands.py`: 237 of 414.
  - `detection.py`: 270 of 623.
  - `cli.py`: 386 of 1309.
  - `quota.py`: 128 of 268.
  - Whole package: about 1,739 of about 4,400.
- **Problem:** A grep for history markers (`CRITICAL|HIGH|MEDIUM|Important finding`, `recurrence guard`, `superseded`, dated fixes, `D-NN`) hits:
  - Code: `cli.py` 46, `detection.py` 23, `dispatch_injection.py` 23, superpowers `cli.py` 18, `commands.py` 14.
  - SKILL docs: superpowers 22, GSD 9.
  - These are change-log narratives ("an earlier draft exited…", "fixed 2026-08-31"), not the reasons the code is the way it is.
  - Some are now false. `gsd_cross_ai.py:1-4` says "No wrapper program… lives in this plan at all", while the SKILL now stores a wrapper. `adapter.py:2` says "never a subprocess dispatch".
- **Fix:** Keep the one-line reasons. Move the history to git, where it already lives. Rough gain: about 1,000 lines out of `ai_kit_spec/`, plus about 30% off the superpowers SKILL.

---

## Instruction artifacts (SKILL.md and references)

### Token weight per invocation (VERIFIED: `wc -l`/`wc -c`, tokens ≈ chars/4)

| File | Lines | ~Tokens | Loaded when |
|---|---|---|---|
| ai-kit-spec-review/SKILL.md | 515 | 9,228 | every review |
| ai-kit-spec-review/references/cross-ai-dispatch.md | 221 | 3,555 | MANDATORY unless --no-cross-ai |
| ai-kit-spec-review/references/apply-findings.md | 131 | 2,006 | MANDATORY when Issues Found |
| ai-kit-spec-review/references/loop-diagram.md | 69 | 869 | optional |
| ai-kit-spec-review/references/routing-table.md | 20 | 370 | optional |
| ai-kit-spec-review/references/cli-profiles/*.md | 354 | 4,476 | config wizard only |
| ai-kit-spec-review-checklist/SKILL.md | 296 | 4,411 | each reviewer subagent, each iteration |
| checklist frameworks/<id>.md | 39-72 | 439-1,093 | one per reviewer |
| checklist frameworks/SCHEMA.md | 150 | 2,238 | only when learning a new framework |
| ai-kit-spec-review-fixer/SKILL.md | 115 | 2,669 | each fixer subagent |
| ai-kit-spec-config/SKILL.md | 338 | 7,694 | every config run |
| ai-kit-spec-config/references/cli-model-selection.md | 315 | 5,603 | MANDATORY when any CLI kept |
| ai-kit-spec-execute/SKILL.md | 79 | 1,632 | every execute (router) |
| ai-kit-spec-execute-gsd/SKILL.md | 247 | 4,305 | GSD execute |
| ai-kit-spec-execute-gsd/references/dispatch-notes.md | 46 | 726 | optional |
| ai-kit-spec-execute-superpowers/SKILL.md | 471 | 8,741 | superpowers execute |
| …/references/state-management.md | 165 | 3,344 | MANDATORY (exclusions/resume) |
| …/references/escalation.md | 131 | 2,588 | MANDATORY (escalation) |
| …/SMOKE_TEST_RESULTS.md | 193 | 2,624 | never referenced (ships in skill dir) |

Totals for one invocation:
- **Review orchestrator:** about 14.8k tokens before any work (SKILL, cross-ai-dispatch, apply-findings).
- **Each iteration:** about 5k more per reviewer subagent and about 3.2k per fixer, so a 3-iteration double review is about 40k tokens of instructions alone (INFERENCE from the sums).
- **Superpowers execute:** about 16.3k (router, SKILL, two mandatory references), plus the transcript echo in #4.
- **Config:** about 13.3k.
- **GSD execute:** about 5.9k.

### 16. Duplicated prompt and boilerplate inside `ai-kit-spec-review/SKILL.md` (READ)
- The external-CLI prompt (`SKILL.md:244-276`) and the native prompt (`SKILL.md:312-364`) restate the same contract, and the SKILL itself says they must "mirror verbatim" (`SKILL.md:272-276`).
  - Fix: Keep one template file. Native reviewers can follow "Read CHECKLIST_SKILL_MD" exactly as external ones do. That saves about 45 lines and removes a drift risk.
- The Cleanup section (`SKILL.md:492-515`) is a 24-line story about a past incident behind a 2-line rule.
  - Fix: cut it to the rule.

### 17. Contradictions (READ)
- **Status vocabulary:** see #1. The checklist and fixer emit `Failure`; the orchestrator tables do not list it.
- **GSD adapter story:**
  - The `gsd_cross_ai.py` and `adapter.py` docstrings say "no wrapper / never a subprocess dispatch".
  - `ai-kit-spec-execute-gsd/SKILL.md:129-160` stores a wrapper that dispatches a subprocess.
- **Router claim:** `ai-kit-spec-execute/SKILL.md:79` says the GSD adapter "writes phase-completion state back into `.planning/`". It writes only `.planning/config.json` (READ `gsd_config.py`). GSD's own skill writes phase state.
- **Host coupling:**
  - `ai-kit-spec-review/SKILL.md:173` pins the fixer to `sonnet`, "Claude-only".
  - Step 1 requires the native model to be one of the four Agent-tool aliases.
  - `CACHE_DIR` is `~/.claude/cache/…`.
  - All of this conflicts with the five-host scope and with the "native must be host-agnostic" decision in user memory. Inference: the native and fixer branches only work in Claude Code.
- **Profile precedence:** `SKILL.md` Step 0.5.B lets a cached profile younger than 180 days win over the bundled seed. When ai-kit ships a corrected seed, the user keeps the old cached copy for up to 6 months (INFERENCE).
  - Fix: prefer the seed unless the cache entry is for a framework that has no seed.

### 18. Routing descriptions collide (READ, from the skill listing in this session)
- **`ai-kit-spec-execute`** ("execute/run/implement a plan or phase") overlaps with `gsd-execute-phase`, `superpowers:executing-plans` and `superpowers:subagent-driven-development`. Typing "execute phase 3" can land in either family.
- **`ai-kit-spec-review-checklist`** ("Use when a design, spec, requirements, or plan document has been produced and needs review before the next step") is nearly the same trigger as `ai-kit-spec-review` ("needs review-and-fix before the next step"). A plain "review my spec" can load the checklist alone: a report with no fix loop.
- **`ai-kit-spec-review-fixer`** is an internal subagent skill, but its description reads like a user entry point.
- **`ai-kit-spec-config`** ("cross-AI reviewer config setup… detects installed CLIs/models") overlaps with `ai-kit-gsd-curated-config` ("cross-AI execution/plan-review CLI+model selection from live-detected … candidates").
- **Fix:**
  - Start the checklist and fixer descriptions with "Internal: dispatched by ai-kit-spec-review; not for direct invocation."
  - Narrow the router to "…when it is unclear whether the plan is GSD or superpowers". Better still, delete the router (#19).
  - Add a "use X instead when…" line to each of the two config skills.

### 19. The router skill costs about 1.6k tokens to do 3 if-checks (READ)
**Where:** `ai-kit-spec-execute/SKILL.md` (79 lines) and `detect_framework.py` (51 lines, 4 checks)

- **What this is:** A skill whose only job is to pick the GSD or superpowers adapter.
- **Problem:** About 25 of its lines resolve a path to a script that checks for `.planning/PROJECT.md` and `docs/superpowers/plans/`. The model can apply that rule from three lines of prose.
- **Fix:** Delete the router and its tests. Put the precedence rule (conversation signal, then document path, then repo markers) into both adapters' descriptions or a shared 5-line section.

### 20. Non-instruction files shipped inside skill directories (READ)
- `ai-kit-spec-execute-superpowers/SMOKE_TEST_RESULTS.md` (193 lines) is a test log. Nothing references it except the plan under `docs/superpowers/plans/`. It gets installed into `~/.claude/skills/`.
  - Fix: move it to `docs/`.

---

## Nice to have (not counted in the 20 above)
- **N1:** `cache_write_json` always writes through the same `path + ".tmp"` (`cache.py:25-29`). Two sessions writing `quota.json` at once can collide on the replace and crash one of them. Fix: use `tempfile.mkstemp(dir=os.path.dirname(path))`. (INFERENCE)
- **N2:** `{model}` is never shell-quoted. Cursor bracket ids glob-expand if a matching file exists in the current directory. VERIFIED: with a file named `m1e` present, `sh -c 'echo m1[effort=high]'` printed `m1e`. Fix: quote `{model}` in `render_reviewer_command`, once #2's single-level quoting is in place.
- **N3:** `render-toml --out` renders twice (`cli.py:1160-1166` plus `cfg_write_toml`), so every validation WARNING prints twice.
- **N4:** The test run prints JSON and TOML to stdout, which buries real failures in noise.

About 6 smaller items were left out, such as `render-command`'s missing index check and duplicate keys in `cfg_merge_reviewers`.

---

## Delete / merge / split candidates
- **Delete:**
  - `render-command`, `prepare-cross-ai-guidance`, `build_gsd_cross_ai_guidance`, `_unimplemented_execute_command`, `write_resumable_state` (the wrapper), and the `affinity_table` parameter (#12).
  - `dispatch_with_heartbeat` (#13).
  - The `ai-kit-spec-execute` router skill (#19).
  - Review-history comments (#15).
  - `SMOKE_TEST_RESULTS.md` from the skill dir (#20).
- **Merge:**
  - The two `assemble_candidates` into one in `execute_selection.py` (#3, #14).
  - The two codegraph-prepare blocks into one in `detection.py` (#6).
  - The signal lists and native-runtime sets (#14).
  - The two reviewer prompts into one template (#16).
  - The five path-resolution blocks into one `ai-kit-spec.py paths` subcommand (#14).
- **Split:**
  - `ai_kit_spec/cli.py` `main()` holds 22 subcommands with inline business logic in one function of about 660 lines (`cli.py:647-1309`). For example, `fetch-model-catalog` alone is about 150 lines of control flow (`cli.py:915-1065`). Move that body into `model_catalog.refresh_catalog(...)` so it can be tested without argparse. Leave the other subcommands, which are already thin.
  - Do not split by line count anywhere else.

## Top 5 highest-value fixes
1. **#1:** a closed status vocabulary in `review_reports.py` plus a `Failure` row in the SKILL tables. A false "Approved" is the worst output this family can produce.
2. **#2:** quote the claude/grok `sh -c` script once as a whole, plus tests with a spaced path. It is a crash and an injection path in every write-capable dispatch.
3. **#3, with #14:** one shared `assemble_candidates`, and thread `effort`/`service_tier` into `WRAPPER_COMMAND`. GSD runs then honor the user's curated config.
4. **#4 and #5:** write the dispatch result to a file instead of argv, and narrow the "quota" match. Both are cheap and stop crashes and silent re-runs on a dirty tree.
5. **#6:** timeouts on the codegraph checks, and an opt-in for the global install. This stops hangs and undisclosed changes to global CLI configs.

**Verdict:** The tests pass and the design is careful, but four confirmed bugs sit on paths no test covers: the false Approved, broken quoting, GSD config drift, and argv overflow. Fix 1-4 first.

**Lean:** about -1,300 lines possible (about 1,000 of comment and history text, about 180 of dead code and tests, about 55 from the dispatcher merge, about 130 from deleting the router). That would also cut about 25-35% of the tokens in the superpowers, review and GSD SKILL docs. -0 dependencies; the runtime is already stdlib-only.

**Not checked:**
- `skills/_shared/ai_kit_rules_common/` was only sized (2,022 lines, 12 modules). It is not used by the spec family: no `ai_kit_rules_common` import exists under `skills/ai-kit-spec-*`.
- `model_catalog.py`, `model_matcher.py` and `model_ranker.py` were only outlined, as was the body of `ai-kit-spec-config/SKILL.md` Steps 1-4.
- `references/escalation.md` and `state-management.md` were only measured.
- No live CLI was run, so the opencode default-permission point (#9) and probe cold-start times (#8) are inference.
