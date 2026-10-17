# Ponytail review: Phase 19 code (`git diff f3f42e6..HEAD`, 10 files, +7666/-12)

1. What it does: `tests/gsd_curated_eval.py` (4,340 lines) is the dev-only matrix, fixture, run, grade, secret-scan and smoke helper; `tests/test_gsd_curated_eval.py` (3,075 lines) is its hermetic suite. The rest is the e2e matrix module, gsd-core 1.17 support, test-group wiring and SKILL.md prose.
2. Two correctness bugs. The grader decides "is this a write/apply" with padded substrings, so `grep -n config-set SKILL.md` counts as the first config write (I checked this live). The smoke's matrix step also passes on a failing matrix.
3. Most of the bloat comes from growing things one fix at a time: about 12 pairs of near-identical helpers (`_abs`/`_abs_path`, 4 sha helpers, 2 JSON writers, 5 JSON readers, 2 tree hashers, 2 set-entry maps...). Six dispatch functions route check names that one dict could hold. Five copies of the `cli.main` + `which_fn` lambda boilerplate, and four copies of the `recommend` flags.
4. The ask detector got four commits of whack-a-mole (19-07, 19-09 x3). A bare `?` and a bare `please` still count as asking. `_offers_choice` is applied in C but not in E, nor in the grouped-question check.
5. Nothing below conflicts with a locked decision in 19-CONTEXT.md. Rough lean estimate: -230 to -280 lines from `tests/gsd_curated_eval.py`, with no change in behavior apart from the bug fixes.

## HIGH

### H1. Substring "needles" count non-product commands as writes, applies and invented values
- **Where:** `tests/gsd_curated_eval.py:857-868` (`WRITE_NEEDLES`), `:1195-1206` (`first_write`), `:1503` (`real=first_bash(evs, " apply ", ...)`), `:1588-1593` (`_asks_not_invents` "invented"), `:1700-1704` (`_exec_disabled` "typed"), `:1404-1407` (`_is_approval`).
- **Finding:** These checks test `" config-set " in f" {command} "` on the raw Bash string, so any read-only command that mentions a verb counts. I checked live that `first_write([bash("grep -n config-set skills/.../SKILL.md")], True)` returns the event, and that `first_bash([bash("rg -n ' apply ' SKILL.md")], " apply ", "--dry-run")` returns it as the real apply. Agents often grep SKILL.md for subcommands. The effect: C `no_real_apply` and `asks_not_invents` fail falsely; E `apply_after_scripted_answer` and the "before the first write" cut point used by `nothing_dropped_silently` and `review_pass_shown` move to the grep; `real` can point at a grep, and then every workflow check grades the wrong event. This is the grader's core primitive, and it has no test with a non-product command.
- **Fix:** Use one rule built on the `_segments` you already have. Add `_call(seg) -> (verb, argv) | None`: skip leading `VAR=value` words. A segment counts as a call only when its first word is `python3`/`python`/`node` (or a path ending in `.py`/`.cjs`), and its verb is the first non-flag word after the script (this covers `python3 "$ENTRYPOINT" apply`, because shlex keeps `$ENTRYPOINT` as one word). Then `first_write` checks `verb in WRITE_VERBS` (the needle tuple without padding). `real` becomes the first call with verb `apply` and no `--dry-run`. `_is_approval` becomes verb `followups` plus `--approve` in argv. `_asks_not_invents`, `_exec_disabled` and `_set_pairs` read `(verb, argv[1])` from the same helper. Add one test: a `grep -n config-set SKILL.md` event must not be a write. This deletes the padding logic and the duplicated verb scans.

### H2. The smoke's matrix step reports pass when the matrix fails
- **Where:** `tests/gsd_curated_eval.py:4117-4127` (`_run_matrix_step`), `:4199-4200` (`render_smoke_evidence`).
- **Finding:** `_step` marks a step ok whenever `fn()` doesn't raise. `run_matrix` returns mismatches and a vacuous Control 1 as data and never raises for them, so a failing matrix gives `ok: True`, the smoke exits 0 (`:4158`), and the evidence says "matrix ran: N checks". The evidence then prints `control.get('verdict', 'recorded')`, but no control dict has a `verdict` key, so every control always reads "recorded", even `ok: False`.
- **Fix:** In `run()`, `if _matrix_failed(holder["matrix"]): raise SystemExit(_render_matrix(holder["matrix"]) or "matrix FAILED")`. In the renderer, print `'ok' if control.get('ok') else 'FAILED'`. Add one hermetic test with a fake ctx whose matrix has a mismatch, asserting the step is not ok.

## MEDIUM

### M1. The "keep rows counted" half of `full_diff_shown` passes on any digit
- **Where:** `tests/gsd_curated_eval.py:1552-1559`.
- **Finding:** `str(len(keep)) not in prose` passes whenever the single digit appears anywhere before the apply. With one keep row, "gsd-core 1.17.0" passes. The check's own rule text (`:921`) only claims add/change/remove.
- **Fix:** Delete the keep sub-rule (`keep`, `kept_named` and the `if`, 4 lines). The check then does exactly what its rule says. If keep rows must be covered, require `rf"\b{len(keep)}\b[^\n]{{0,40}}\b(keep|unchanged)"` instead.

### M2. Ask detection: regex holes, and the choice rule applied in only one scenario
- **Where:** `tests/gsd_curated_eval.py:1600-1625` (`_ASK_RX`, `_asks_user`), `:1594` (C uses `_asks_user or _offers_choice`), `:1685` (E uses `_asks_user` only), `:1393` (`_grouped_question` uses `_asks_user` only).
- **Finding:** A bare `\?` matches URLs and globs ("See https://x/a?b=1"), and the mid-sentence `\bplease \w+` matches "Please note: I applied it." Both return True today (checked). The alternatives `(choose|pick) (one|a model)` and `tell me (which|...)` mostly overlap the sentence-start verb branch. Separately, a reply that only lists the choices passes `asks_not_invents` in C but fails `asks_despite_pressure` in E.
- **Fix:** Use one rule: `r"\?(\s|$)|what i need from you|(^|[.!:]\s+|\n[\s>*-]*)(\*\*)?(please\s+)?(reply|tell me|let me know|answer|confirm|choose|pick)\b"`. Every existing assertion in `test_asks_user_accepts_explicit_requests` still holds (checked), and both false positives above become False. Then add `_asks(text, candidates) = _asks_user(text) or _offers_choice(text, candidates)` and call it from all three sites.

### M3. Six dispatch functions route check names that one dict could hold
- **Where:** `tests/gsd_curated_eval.py:1509-1539`, `:1571-1581`, `:1667-1680`, `:1742-1772`.
- **Finding:** `_scored` -> `_b_outcome`/`_workflow_verdict`/`_other_verdict` -> `_c_outcome` -> `_e_outcome`. A check name means the same predicate in every scenario. Yet `nothing_dropped_silently` is written twice (`:1511`, `:1759`), `remove_rows_shown` is routed twice (`:1536`, `:1753`), and the D and E workflow branches are identical (`:1766-1769`). Pylint does not run on `tests/`, so no limit forced this split.
- **Fix:** Use one `_PREDICATES: dict[str, Callable[[_Ctx], Verdict]]` keyed by check name (the existing lambdas, with `ctx.config or {}` inline), and `_scored = lambda s, ctx, check: _PREDICATES[check.name](ctx)`. That deletes 6 functions (about -55 lines). Add an assert that every name in `CHECKS` has a predicate, so the table and the dict cannot drift.

### M4. About 12 near-duplicate helpers inside the one file
- **Where:** `tests/gsd_curated_eval.py`:
  - `_abs`:144 = `_abs_path`:2298;
  - `_file_sha`:176 = `_sha_or_none`:3957; `_sha256_file`:2302 = the imported `_sha256`;
  - `_write_json`:344 vs `_dump_json`:2311 (only the indent differs);
  - `_run_json`:948 and `_candidates`:988 are the same body, and both re-implement `plan_io.read_json_object`, which already returns `(None, None)` for a missing file;
  - `_json_or_none`:3211 vs `_json_object`:2239;
  - `_tree_sha`:250 vs `tree_sha256`:3581;
  - `_set_entries`:488 = `_set_map`:1717, and `_unoverridden`:701-703 rebuilds the same set;
  - `_load_plan`:667 = `_load_plan_file`:3663 (`_refusal` is already a `SystemExit`);
  - `_cache_sha`:2452 = `_cache_sha_of`:3843;
  - `_make_scratch_project`:2355 vs `_scratch_project`:3820 (git init plus the gsd-core symlink);
  - `_live_row_tokens`:373 repeats the predicate in `_live_row`:2121.
- **Finding:** These are copies that must change together. Some already drift: the two tree hashers treat symlinks differently, and the two writers produce different bytes.
- **Fix:** Keep one of each pair and make the other's callers use it:
  - `_abs`, `_sha256`, a `_sha_or_none` (Path or str), `_write_json`, `plan_io.read_json_object(...)[0]`, `_json_object`, `_tree_sha`, `_set_entries` and `_load_plan`;
  - `_cache_sha(cache_dir)`;
  - one `_scratch_project(dir, with_planning)`;
  - `_live_row_tokens = lambda l: _HEX16.findall(l) if _live_row(l) else []`.

  Saves about 70 lines. The tests that call `tree_sha256` switch to `_tree_sha`.

### M5. The `cli.main`, inventory and recommend boilerplate is repeated in fixture and smoke
- **Where:** `tests/gsd_curated_eval.py`:
  - `_live_inventory`:2656 vs `_inventory`:3850, which do the same steps: `assert_no_probe`, `cli.main inventory`, the cache-sha guard, write the output, parse it;
  - `_recommend`:2680 vs `_recommend_to`:3880, with the four-flag list repeated at `:2695`, `:2885`, `:2915` and `:3886`;
  - the `which_fn=lambda name, **_kw: node_bin if name == "node" else shutil.which(name)` + `redirect_stdout` block repeated at `:2668`, `:2842`, `:3862`, `:3920` and `:4085`;
  - `_real_apply_or_fail`:3931, `_SmokeEnv`:3946, `_real_apply_fault`:4069 and `cli_main_apply`:4078 are four wrappers around one `cli.main(["apply", ...])`.
- **Finding:** The same inventory, recommend and apply invocations are written two to five times.
- **Fix:**
  - One `_cli(argv, node_bin, env, run_fn=subprocess.run) -> (code, stdout, stderr)`.
  - One `_inventory(node_bin, env, project, out, cache_sha, host=None)`, used by both fixture and smoke.
  - One `_recommend(inv, profile, rigor)` with the y/y flags inside.
  - `_real_apply_or_fail(ctx, ...)` that calls `_real_apply_fault(..., subprocess.run)` and checks the code. Delete `_SmokeEnv`.

  About -60 lines.

### M6. `product_module` works around a test-cleanup leak instead of fixing it
- **Where:** `tests/gsd_curated_eval.py:136-141`; root cause in `tests/test_ai_kit_gsd_curated_config.py:522-535` (`_reimport_with_ai_kit_spec_blocked` pops `sys.modules` but leaves the degraded module bound on the package attribute).
- **Finding:** The eval uses the shim for 2 modules but still does a lazy `from ai_kit_gsd_curated_config import cli/apply/host/catalog_adapter` in 9 places (`:2418`, `:2659`, `:2789`, `:2792`, `:2837`, `:3611`, `:3672`, `:3852`, `:3905`, `:4081`, `:4229`). These read the same leaked attribute, so the shim protects only part of the file. It matters only when modules share one process, because `run_unittest_parallel` gives each module its own.
- **Fix:** Fix the leak once in the v1 test helper: save `getattr(pkg, module_name, None)` and `addCleanup(setattr, pkg, module_name, saved)`. Then delete `product_module` and its test (`tests/test_gsd_curated_eval.py:1702-1740`), and hoist the product imports to the module top next to `config_backup, plan_io, presets`.

### M7. `_redirected_reports` reads a file outside the run dir at grade time
- **Where:** `tests/gsd_curated_eval.py:1143-1160`.
- **Finding:** For `apply ... > /tmp/r.json`, the grader opens `/tmp/r.json` when it grades, not when the run happened. If a later cell or scenario writes the same path, re-grading the earlier cell reads the wrong report. So `grade` is not a pure function of the run dir, as D-13 intends.
- **Fix:** Accept only targets inside the run dir (the fixture's `TMPDIR` is `<run>/tmp`, so `mktemp` output qualifies). Thread `ctx.run` into `report_json` as one optional arg used only here. Or mark the limit with `# shortcut: reads the redirect target at grade time; restrict to the run dir if cells share paths`.

### M8. Project (b) records a `diff` that is always empty, and its test checks its own copy of the logic
- **Where:** `tests/gsd_curated_eval.py:4108-4110`; `tests/test_gsd_curated_eval.py:2914-2932`.
- **Finding:** A real (non-dry-run) apply report has no `diff` key; only the dry-run report does (`apply.py:306`, and `_fail_report`). So `diff` is always `[]` and the step says "0 diff rows". The test `test_project_b_records_key_paths_not_values` builds `key_paths` inside the test with the same comprehension and only checks the renderer. It would still pass if `_smoke_project_b` recorded values.
- **Fix:** Drop the `diff` field (2 lines). Make the test drive `_smoke_project_b` through a stubbed `_real_apply_or_fail` that returns a report holding a `SENTINEL-VALUE`, and assert the sentinel is absent from `result["key_paths"]`.

## LOW

- **L1.** `tests/gsd_curated_eval.py:1775-1780`: `_status` is dead (never called), and `render_markdown:1836-1840` re-implements it inline. Call `_status`-style logic from the renderer, keyed off the row dict, or delete `_status`.
- **L2.** `tests/gsd_curated_eval.py:1223`: in `text_between`, `start is None or end is None` cannot happen because `_position` always returns an int. Delete the None checks.
- **L3.** `tests/gsd_curated_eval.py:2162-2164`: `gsd_version_supported` is a one-line alias of the imported `gsd_core_line_supported`. Call the original directly and update the 2 test references.
- **L4.** `tests/gsd_curated_eval.py:463-509`: `inheritance_promised` is a speculative option. Its own docstring says "nothing in this phase sets it", and D-10 does not ask for it. Delete the keyword from `promised`, `compare` and `_mismatches`, plus `test_inheritance_promised_accepts_empty` (`tests/test_gsd_curated_eval.py:117`); Phase 20 can add it when something sets it.
- **L5.** `tests/gsd_curated_eval.py`: there are 25 `# pylint: disable=...` comments, but pylint never runs on `tests/` (`.pre-commit-config.yaml:30`, `files: ^(tools|skills)/`). They are noise and they force odd ruff wrapping (`:2789-2791`, `:3611-3613`, `:4229-4231`). Delete them (this pairs with the hoisted imports in M6).
- **L6.** `tests/gsd_curated_eval.py:2218-2232`: `_render_matrix` explains a Control 1 failure but prints nothing for a failing Control 2, so the text output is a bare "matrix FAILED". Append `control 2 mismatches: <agents>`.
- **L7.** `tests/gsd_curated_eval.py:2183-2190` and `:4224-4228`: in `_cmd_matrix`, the host check repeats `run_matrix`'s own `_refusal(2, ...)`, and `main` already maps that to exit 2. `print(reason or "no node executable")` is also redundant, because `gsd_run_reason` already returns that text when node is None. Delete the host pre-check and print `reason`. `_matrix_failed(result)` is computed twice (`:2200`, `:2204`); compute it once.
- **L8.** `tests/gsd_curated_eval.py:2262`, `:2813`, `:2946`, `:2959`: `ROUTERS` duplicates `ROUTER_MODEL`/`ROUTER_REVIEW`; `_b_facts` hardcodes both router literals; `_build_b` re-types `POISON_DEFAULTS`. Use `ROUTERS = (ROUTER_MODEL, ROUTER_REVIEW)` and refer to the constants.
- **L9.** `tests/gsd_curated_eval.py:3350-3372`: `_shadow_failures` has its own `.split()`, quote-strip and `cd` regex tokenizer, while `_argv_of`/`_segments` (shlex) exist. `_redirected_reports:1148` has a second `VAR=value` regex. Iterate `_segments(command)`, track the last `cd` segment's argument, and share one `_assignment(word)` helper.
- **L10.** `tests/gsd_curated_eval.py:2765-2784`: `_e_answer_pairs` uses `_candidate_value` + `json.dumps`, which gives the same output as `_choice_raw:3684` for every candidate shape the plan emits. Use `_choice_raw(cands[0])` and keep `_candidate_value` only for `_write_candidates`.
- **L11.** `tests/gsd_curated_eval.py:4032`: `KEEP_LIMIT = config_backup.KEEP` is an alias defined after its first use (`:4017`). Use `config_backup.KEEP` directly.
- **L12.** `tests/test_ai_kit_gsd_curated_config_matrix.py:50,55,115`: `scratch_parent` is created and removed but nothing ever writes there (`run_matrix` uses its own `mkdtemp`). Delete it. The `tempfile.gettempdir()` root in the same loop already covers it.
- **L13.** `tests/test_curated_config_apply_e2e.py:258-268`: `TestRealApply` re-implements the version skip that `_gsd16_or_skip` (`:155-168`) does. Call `_gsd16_or_skip(self)`.
- **L14.** `skills/ai-kit-gsd-curated-config/SKILL.md:126-129`: the hand-written family list matches `presets.MANAGED_PREFIXES` today, but no test pins it. Add one assertion to `TestSkillDocCommands.test_required_statements` that each `MANAGED_PREFIXES` entry appears as `` `<prefix>*` ``. Also, the anti-pattern rows at `:294-295` restate step 4 (`:131-139`) nearly word for word. They can go in the next skill-judge round; this is not urgent, because the digest-bound evidence would need re-binding.

## Not checked

I did not run `make test` or the live matrix/smoke (the review was read-only, with no live AI-CLI runs). I read but did not re-derive the fixture builders (`_build_*`, `_materialize_v1`) or the PTY/process-reaping paths in depth. If M4 or M5 changes `tree_sha256` or the fixture helpers, the H1 and M4 changes also touch `tests/test_gsd_curated_eval.py` (about 240 tests). Run `make test-unit` after them.
