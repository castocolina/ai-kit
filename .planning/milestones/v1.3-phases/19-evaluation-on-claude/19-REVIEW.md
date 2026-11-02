---
phase: 19-evaluation-on-claude
reviewed: 2026-10-17T21:59:59Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - .pre-commit-config.yaml
  - Makefile
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md
  - skills/ai-kit-gsd-curated-config/evals/02-opencode-routers-no-catalog.md
  - skills/ai-kit-gsd-curated-config/evals/03-v1-written-config.md
  - skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md
  - skills/ai-kit-gsd-curated-config/references/v1-path.md
  - tests/gsd_curated_eval.py
  - tests/test_ai_kit_gsd_curated_config_matrix.py
  - tests/test_curated_config_apply.py
  - tests/test_curated_config_apply_e2e.py
  - tests/test_gsd_curated_eval.py
  - tools/run_unittest_parallel.py
findings:
  critical: 3
  warning: 8
  info: 10
  total: 21
status: resolved
---

# Phase 19: Code Review Report

**Reviewed:** 2026-10-17T21:59:59Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Scope: the diff `f3f42e6..HEAD`. Most of it is the new harness `tests/gsd_curated_eval.py`
(about 4,340 lines) and its unit suite. The Makefile, pre-commit, runner and e2e-guard edits are
mechanical and correct: the new modules are in the right groups, and `gsd_core_line_supported`
is shared by both guards. I confirmed every finding below against the source. Several I also
reproduced by calling the helpers on synthetic input (`SECRET_RX`, `first_write`,
`_live_row_tokens`, `_smoke_placeholders`), or by reading the committed grade records under
`.planning/phases/19-evaluation-on-claude/pressure/`.

Main concerns:
1. The grader has no turn-boundary gate between the dry run and the real apply in B and D.
   SKILL.md now names this anti-pattern explicitly.
2. Committed grading records can carry credential values. The secret scan meant to catch them
   misses common key shapes.
3. A `claude -p` child with unrestricted Bash on the real HOME keeps running after the harness
   is interrupted.
4. Verb detection works on substrings and ignores command segments. It fails compliant agents
   and hides chained dry-run+apply calls.

## Critical Issues

### CR-01: B/D graders pass "dry run and real apply in one turn", which SKILL.md forbids

**File:** `tests/gsd_curated_eval.py:1248-1271`, `1542-1560`, `1529-1539`
**Issue:** `_accepted_dry_run` checks four things: order (`dry` before `real`), same `--plan`/`--project-dir`, a successful dry-run report, and no `plan-set` in between. `_full_diff_shown` and `_remove_rows_named` check only that the keys appear in assistant text *anywhere before* the real apply (`text_before`). None of the B or D checks compares `real["turn"]` with the turn of the dry run that was shown. Picture an agent that runs the dry run, prints every row by its full key, and runs `apply` in the same turn. It passes every gating B and D check. Yet SKILL.md step 4 (lines 139-142) requires "end the turn and apply only after the user answers". The anti-pattern table lists "Dry run and real apply in one turn". Eval 03's expected behavior 5 is "Does not apply without the user's answer to the diff". Only scenario E has a turn-based check (`apply_after_scripted_answer`). The committed `D-green.grade.json` shows the gap in use: dry run in turn 1, then another dry run *and* the real apply both in turn 2. The grader accepted the turn-2 dry run without asking whether its rows had been shown in an earlier turn.
**Fix:** Make the turn boundary part of acceptance, and add a negative test:
```python
def _accepted_dry_run(evs, real):
    ...
    shown = [d for d in dry_runs_before(real) if d["turn"] < real["turn"]
             and _diff_rows(report_json(evs, d)) == _diff_rows(report_json(evs, dry))]
    if not shown:
        return None, "no dry run with the same rows shown in an earlier turn"
```
Also add a `test_dry_run_and_apply_same_turn_fails` case for B and D.

### CR-02: Committed grading records can carry secrets; the backstop scan misses common key shapes

**File:** `tests/gsd_curated_eval.py:882-888`, `1877-1889`, `1931-1953`, `3151-3158`
**Issue:** Three facts combine into a leak path.
- (a) `_cell_env` builds the agent env with `child_env(...)`. That copies the operator's whole `os.environ` (`runner_dispatch.child_env`, line 135), so every API-key or token variable reaches an unattended agent. That agent has `--allowedTools Bash,...` and the real HOME.
- (b) `record_of` -> `_commands_record` stores `report_json(evs, event)` for *every* Bash command. That is the full last JSON object (or Python dict repr) of any tool output, not only apply reports. An agent that runs `cat` on an auth or config JSON file therefore puts the parsed object, untrimmed, into `pressure/*.grade.json`, which is committed evidence.
- (c) `SECRET_RX`, the T-19-10 backstop, is case-sensitive and narrow. I reproduced misses on an `apiKey` JSON field holding 22 letters (opencode's provider key field), on `"key": "xai-..."` (the auth.json shape), and on `ghp_...`, `AIza...` and `*_TOKEN=...`.

Scenario C (an opencode host) is exactly the case where an agent inspects opencode provider config.
**Fix:** Close the leak at the source and widen the scan:
- In `_commands_record`, store only apply, dry-run and followups reports (`"dry_run" in o or "applied" in o or "results" in o`), never arbitrary JSON objects.
- In `_cell_env`, start from a minimal allowlist (`PATH`, `LANG`, `TERM` plus the fixture env and HOME) rather than `os.environ`.
- Extend `SECRET_RX` with `re.I` on the key-name branches, a `"(api_?key|key|token|secret)"\s*:\s*"[^"]{12,}"` branch, and the prefixes `ghp_|gho_|glpat-|xai-|AIza`.
- Add a canary for each new shape.

### CR-03: Interrupting the harness orphans a full-permission `claude -p` on the real HOME

**File:** `tests/gsd_curated_eval.py:3161-3193`
**Issue:** `_run_one_turn` starts `claude -p` with `start_new_session=True`, so a Ctrl-C or SIGTERM sent to the harness's process group never reaches the child. The only cleanup is the `except subprocess.TimeoutExpired` branch and the trailing `_signal_group(..., SIGKILL)`. Neither runs when `proc.wait(timeout=900)` raises `KeyboardInterrupt`, or when any other exception unwinds. The result is an unattended agent that keeps running for up to 15 minutes. It has unrestricted Bash, the real login and the real HOME, spends quota, and may write. This breaks the AGENTS.md rule "Kill/stop any ephemeral process ... never leave it orphaned". No test covers it: `TestRun` injects only `TimeoutExpired`.
**Fix:**
```python
proc = seams.popen_fn(...)
try:
    proc.wait(timeout=RUN_TIMEOUT)
except subprocess.TimeoutExpired:
    timed_out = True
    ...
finally:
    _signal_group(seams, proc.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5)
    _signal_group(seams, proc.pid, signal.SIGKILL)
```
Then add a test where `wait` raises `KeyboardInterrupt` and assert that SIGKILL was sent to the group.

## Warnings

### WR-01: Write/apply detection matches substrings of the whole command, not the verb of a command segment

**File:** `tests/gsd_curated_eval.py:1195-1206`, `1503`, `1584-1597`, `1700-1704`
**Issue:**
- `first_write` drops a whole Bash call when `"--dry-run"` appears anywhere in it. Otherwise it matches padded substrings such as `" config-set "` across the full command text. `_context.real = first_bash(evs, " apply ", exclude="--dry-run")` does the same.
- I reproduced two consequences. First, `grep -n config-set SKILL.md` counts as the first write. So a compliant C agent that greps its own docs fails `no_real_apply`, and `_asks_not_invents` fails too (`" config-set " in command`, so `invented` is set). Second, `python3 E apply --dry-run ... && python3 E apply ...` yields `first_write = None` and `real = None`. A chained dry-run+apply is invisible: C `no_real_apply` passes, and B/D fail with the misleading reason "no real apply".
- `_segments` and `_segment_with` already exist but are not used here.

**Fix:** Detect verbs per segment. A segment is a write when its argv has the entrypoint or `gsd-tools.cjs` followed by a write verb, and `--dry-run` is not in *that segment*. Use the same predicate for `real`, `first_write`, `invented` and `typed`. Add negative tests for `grep config-set` and for a chained dry-run+apply.

### WR-02: B and E scripted answers no longer line up with the SKILL.md flow, so the approval path is never exercised

**File:** `skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md:25`, `skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md:24`, `tests/gsd_curated_eval.py:1439-1445`
**Issue:**
- The comments say B's turn 3 comes "after the dry-run report and the follow-up grouping" and E's turn 3 comes "after the grouped follow-ups". But SKILL.md step 4 now ends the turn after the dry run. A compliant agent therefore treats the turn-3 answer ("Yes, run them." / "Yes.") as approval *of the apply*, and no answer is left for the follow-ups.
- Every committed B and E green record (`B-green`, `B-green-opus`, `E-green`, `E-green-opus`) has the dry run in turn 2 and the apply in turn 3. Each passes `grouped_followup_approval` through the shortcut "grouped question asked; no scripted answer left to approve".
- So in B and E, the gating check for the fingerprint, `--require` and row return codes has never run on real output.

**Fix:** Add a fourth scripted answer to B and E ("Yes, run the follow-ups."), and correct the turn comments. Or make the shortcut non-gating when the scenario's eval file promises a follow-up answer.

### WR-03: Smoke evidence placeholders: home is replaced before the worktree, and the work dir is never labelled

**File:** `tests/gsd_curated_eval.py:4170-4180`
**Issue:**
- `_smoke_placeholders` replaces `home` before `repo_root`. On this machine `HOME` is under the symlinked `/home`, but `REPO_ROOT` resolves under `/var/home` (`/home -> var/home`). A failing step's detail therefore renders as `/var<home>/<repo path>/...` (reproduced). This is the same bug `_placeholders` fixed in 19-07 (lines 1850-1859).
- Only `scratch_a` and `scratch_b` are labelled. Any detail that names `work` itself (`/tmp/smoke-XXXX/plan-a.json`, `.../xdg`) keeps its absolute path.
- `test_evidence_has_placeholders_only` (test file 2896-2912) uses `home=self.tmp`, which is not a prefix of `REPO_ROOT`, so the test cannot catch either problem.

**Fix:** Replace in this order: `work`, then `repo_root`, then both `home.resolve()` and `home`. Pass `work` into the result. In the test, use a home that is a prefix of the repo path.

### WR-04: The transcript cleanup and the `.claude.json` check compute Claude's project key wrongly and fail silently

**File:** `tests/gsd_curated_eval.py:3383-3384`, `3339-3347`, `3527-3530`
**Issue:**
- `_transcript_dir` replaces only `/` and `.`, and works on the unresolved path. Claude Code keys its transcripts by the realpath of the cwd. This repo's own memory dir is `-var-home-...` even though `HOME` is `/home/...`. As far as I can tell, Claude Code also maps every non-alphanumeric character to `-`; I did not check that against Claude Code's source.
- Any run dir with `_`, a space or other punctuation, or one reached through a symlink (for example `/home/...`), produces a name that does not match. `_delete_transcript_dir` then hits `FileNotFoundError` silently and leaves the transcript in the real `~/.claude/projects`, contrary to D-12 / jev 19-S1.
- The same unresolved-path comparison makes `_claude_json_projects_failure` miss a gained `projects` key.
- It works today only because `mktemp -d` under `/tmp` happens to produce `[A-Za-z0-9.]` names.

**Fix:** Use `re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(project))` in both places. Record a harness failure when the expected transcript dir does not exist after a turn completed, rather than suppressing it.

### WR-05: The reaper SIGKILLs any process group whose args merely contain the run-dir string

**File:** `tests/gsd_curated_eval.py:3119-3131`
**Issue:** `needle = str(run_dir)` is a bare substring test. Run dir `/tmp/r` matches `/tmp/r2/...`, `/tmp/run-other`, and so on. An operator's `less`, `vim` or `tail -f` on a file inside the run dir also matches. In every case the entire process group is SIGKILLed.
**Fix:** Match path boundaries, for example `re.search(re.escape(needle) + r"(/|\s|$)", args)`. Restrict the kill to processes that descend from the CLI's session (`pgid == cli_pid`), or to processes whose session id is a descendant, not to every process on the box.

### WR-06: A unit test in the pre-commit tier reads and hashes the real home's protected config files

**File:** `tests/gsd_curated_eval.py:315-324`, `tests/test_gsd_curated_eval.py:682-684`
**Issue:** `_cmd_snapshot` calls `snapshot(repo_root, home)` *before* it checks whether `--out` or `--check` was given. `test_snapshot_cli_requires_a_mode` calls `ev.main(["snapshot"])` without `--home`. Every `make validate` or pre-commit run therefore reads the real `~/.claude/settings.json`, `settings.local.json`, `CLAUDE.md`, `~/.gsd/defaults.json` and `~/.cursor/cli-config.json`, plus the `~/.claude/plugins/*.json` files, and tree-hashes gsd-core. This breaks AGENTS.md: "Never use uz's real config files ... as a test fixture".
**Fix:** Validate the mode first (`if not args.out and not args.check: return 2`) and only then snapshot. Pass `--home <tmp>` in the test.

### WR-07: Loose evidence heuristics let gating checks pass on incidental text

**File:** `tests/gsd_curated_eval.py:1557-1559`, `1388-1401`, `1600-1606`, `1709-1714`
**Issue:**
- `_full_diff_shown`: a "keep" count passes when `str(len(keep))` appears anywhere in the prose. Any digit qualifies: a version string, `KEEP = 3`, a step number.
- `_grouped_question`: a row counts as named when any of its argv words of 4 or more characters appears in the text. For `effort_sync`, that is `effort` or `sync`, which also occur inside "async".
- `_ASK_RX`: any `?` counts as a question. That includes `$?` in quoted shell, and `\bplease \w+` matches "please note".
- `_router_wins`: passes when `router-env/my-coding` is the value of *any* set entry or of `artifacts[0]` models. It does not check that the router is the execution target, which is what the check name and eval 02 promise.

**Fix:**
- For keep rows, require the count as a token next to "keep" (`rf"\b{n}\b\s+keep"`).
- Name a follow-up row by its `id` or full `purpose` only.
- Drop the `?` and `please` branches, or require them in the last paragraph.
- In `_router_wins`, check the execution-specific location (`artifacts[*].config.models.<runner>` for the runner the prefer order puts first).

### WR-08: Digest binding ignores every evidence row that contains the word "context"

**File:** `tests/gsd_curated_eval.py:373-379`, `2121-2128`
**Issue:** `_live_row_tokens` and `_live_row` treat a row as history when `"context" in line` matches anywhere. The convention is a status cell equal to `context` (19-SKILL-JUDGE.md:19-22). But a live row whose judge name, note or evidence mentions "context" (for example "fresh-context run") is silently exempt from the `token == digest` check. I reproduced that `| green | 0123456789abcdef | fresh-context run |` yields no tokens. A stale digest can therefore pass `digest --check`.
**Fix:** Parse cells and exempt only rows whose status cell is exactly `context` or `superseded` (the same applies to `table_cells`, line 2053).

## Info

### IN-01: Stale docstring in `_seed_runtime_key`

**File:** `tests/gsd_curated_eval.py:761-767`
**Issue:** The docstring says the `refuse_repo_apply` guard "lands in 19-04 ... until then". The guard exists and `_apply_bundle` calls it (line 572).
**Fix:** Delete the "until then" sentence.

### IN-02: The matrix e2e test's `scratch_parent` is unused, and it leaks when `setUpClass` fails

**File:** `tests/test_ai_kit_gsd_curated_config_matrix.py:50`, `53-55`, `115`
**Issue:** `run_matrix` never uses `scratch_parent` (it calls its own `mkdtemp`), so the no-absolute-path assertion on it is vacuous. When `run_matrix` raises in `setUpClass`, `tearDownClass` does not run and the directory stays behind.
**Fix:** Drop the variable, or use `cls.addClassCleanup(shutil.rmtree, ...)` before the run.

### IN-03: Comments claim more than they verify about 1.16 and 1.17 being equivalent

**File:** `tests/test_curated_config_apply_e2e.py:57-64`, `tests/gsd_curated_eval.py:125-133`
**Issue:** The comments say the tables are byte-equivalent between 1.16.0 and 1.17.0 and are "re-verified every run by tests.test_ai_kit_gsd_curated_config_matrix". That test only checks key parity between `MODEL_PROFILES` and `AGENT_TO_PHASE_TYPE` within the *installed* version (`test_key_parity`). It never compares against 1.16, and any `1.17.x` is accepted. AGENTS.md forbids claiming more certainty than was verified.
**Fix:** Reword the comments to "verified once on <date>; the matrix re-checks key parity only".

### IN-04: `_claude_version` has no seam, so unit tests can run a real `claude --version`

**File:** `tests/gsd_curated_eval.py:3387-3396`, `tests/test_gsd_curated_eval.py:861-869`
**Issue:** `_finish_run` always runs `seams.claude_bin --version`. The hermetic `TestRun` seams use `claude_bin="/bin/claude"`, so on a box where that path exists, the unit tier starts the real CLI. It is absent here, so this is latent.
**Fix:** Add a `version_fn` seam to `RunSeams`, defaulting to `_claude_version`.

### IN-05: `test_project_b_records_key_paths_not_values` re-implements the logic it claims to test

**File:** `tests/test_gsd_curated_eval.py:2914-2932`
**Issue:** The test builds `key_paths` itself and then checks only that the renderer prints keys, which the renderer never prints values for anyway. The extraction in `_smoke_project_b` (lines 4107-4109) is never exercised.
**Fix:** Drive `_smoke_project_b` with patched `_inventory`, `_recommend_to`, `resolve_choices`, `_dry_run_unchanged`, `_real_apply_or_fail` (returning a report with a sentinel value) and `validate_applied`.

### IN-06: `_redirected_reports` reads any absolute file a transcript command named

**File:** `tests/gsd_curated_eval.py:1143-1160`
**Issue:** The grader opens `target` whenever it is an absolute path to an existing file, including paths outside the run dir, and its parsed report can end up in the committed record.
**Fix:** Require `target` to resolve under `run` (`pathlib.Path(target).resolve().is_relative_to(run.resolve())`).

### IN-07: SKILL.md wording: "a key the project has now" and a broken line wrap

**File:** `skills/ai-kit-gsd-curated-config/SKILL.md:125`, `140-141`
**Issue:** On a project with no config, `unset` entries are predicted removals (step 4, `"predicted": true`), not keys "the project has now". Line 140 also ends early ("...given before those rows were").
**Fix:** Change it to "a key the project has now, or that `config-new-project` is predicted to copy", and reflow the paragraph.

### IN-08: The shadow-entrypoint check uses a prefix match without a path separator

**File:** `tests/gsd_curated_eval.py:3369-3371`
**Issue:** `resolved.startswith(normpath(allowed))` accepts `.../v1-skill-other/...` and `.../ai-kit-gsd-curated-config-copy/...`.
**Fix:** Use `os.path.commonpath([resolved, allowed]) == allowed`.

### IN-09: `run` does not enforce the protected-set snapshot it depends on

**File:** `tests/gsd_curated_eval.py:3533-3552`
**Issue:** D-12 requires a snapshot and diff around every batch. `run` neither takes a snapshot nor checks one, so the guarantee depends only on the operator following the procedure.
**Fix:** Add an optional `--snapshot F` to `run` that calls `_snapshot_report` after the cell and adds any strict change to `harness_failures`.

### IN-10: `plugins` and `memory_paths` are recorded from init but never gated

**File:** `tests/gsd_curated_eval.py:3303-3313`, `3328-3336`
**Issue:** D-12's reason for using headless runs is to avoid a contaminated baseline. Yet a cell that loaded a user `CLAUDE.md` (`memory_paths`) or plugins passes the harness checks. I did not check whether `--setting-sources project` already empties these fields in practice. Only turn 1's init is checked.
**Fix:** Gate on non-empty `plugins` and on `memory_paths` outside the scratch project, for every turn's init.

---

_Reviewed: 2026-10-17T21:59:59Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
