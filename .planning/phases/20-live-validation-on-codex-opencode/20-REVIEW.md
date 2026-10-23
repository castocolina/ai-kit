---
phase: 20-live-validation-on-codex-opencode
reviewed: 2026-10-18T10:25:00Z
depth: deep
diff_range: 43989c2..2acdada
files_reviewed: 21
files_reviewed_list:
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py
  - skills/ai-kit-gsd-curated-config/references/runner.md
  - skills/ai-kit-gsd-curated-config/references/v1-path.md
  - skills/ai-kit-spec-review/ai_kit_spec/detection.py
  - skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - tests/gsd_curated_eval.py
  - tests/test_ai_kit_gsd_curated_config.py
  - tests/test_ai_kit_gsd_curated_config_matrix.py
  - tests/test_ai_kit_spec.py
  - tests/test_ai_kit_spec_runner_dispatch.py
  - tests/test_ai_kit_spec_runtimes_table.py
  - tests/test_curated_config_apply.py
  - tests/test_curated_config_followups.py
  - tests/test_curated_config_plan_edit.py
  - tests/test_curated_config_recommend.py
  - tests/test_curated_config_script.py
  - tests/test_gsd_curated_eval.py
findings:
  critical: 0
  warning: 12
  info: 9
  total: 21
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-10-18T10:25:00Z
**Depth:** deep (standard per-file review, plus cross-file checks against gsd-core, the raw smoke output under `tmp/p20/headless/`, and the test loader)
**Files Reviewed:** 21 (goldens excluded; `.planning/scripts/cross-ai.mjs` is a render of the template and was not reviewed)
**Status:** issues_found

## Findings summary

| Severity | Count | IDs |
|---|---:|---|
| Critical | 0 | none |
| Warning | 12 | WR-01 to WR-12 |
| Info | 9 | IN-01 to IN-09 |

Main concerns, most important first:
1. The planned == baked check passes when an agent file is missing (WR-01). The opencode check silently skips 29 compact agent files (WR-12).
2. Parts of the smoke evidence are constants, not measurements (WR-05). The paths list is duplicated (WR-08). The committed codex paths list differs from what the harness wrote (WR-09).
3. Some follow-up notes claim more than the evidence shows (WR-06, WR-07).
4. The local install is not isolated from `GSD_HOME`, `CODEX_HOME` and `OPENCODE_CONFIG_DIR` (WR-04).
5. Test reliability: the matrix mixin class is collected as a fourth test class, so the claude matrix runs twice (WR-02). One unit test needs a gitignored gsd-core (WR-10). A pre-existing test reads the real `~/.config/ai-kit/review-spec.toml` (WR-11).

## Summary

Phase 20 adds a host-aware resolve-model oracle and a codex/opencode smoke (local install, planned == baked, labelled artifacts) to `tests/gsd_curated_eval.py`. It also extends the snapshot guard to semantic TOML and opencode trees, adds `--standalone` to template 4, and updates the detection and follow-up wording to match the headless evidence.

The oracle (`promised`/`_host_model`/`_mismatches`/the controls) is sound. I traced the four tier cases and the fail-closed handling of non-zero exits. Every return path of an empty `resolve-model` fails on the tier comparison, so a failed call cannot pass. Template 4 adds `--standalone` to opencode exec and review, and the self-test asserts both (resume is not asserted, see IN-02). The SIGINT `setUp` fix in `tests/test_ai_kit_spec_runner_dispatch.py` is correct: `signal.default_int_handler` is installed per test and the inherited handler is restored with `addCleanup`. The SIGINT tests all live in `TestRunRunnerFake`, and the SIG_IGN caller case (line 396) still runs. No finding there.

The defects are in the smoke harness's evidence and comparison code, in the wording of two follow-up notes, and in test collection and isolation.

## Warnings

### WR-01: planned == baked passes when an agent file is missing; the test pins the bug

**File:** `tests/gsd_curated_eval.py:4268-4275` (used at `:4396` and `:4558`); `tests/test_gsd_curated_eval.py:2939-2944`
**Issue:** `_baked_mismatches` compares with `baked.get(agent) != expected`. On codex the promise is `entries.get(f"model_overrides.{agent}")`, which is `None` for every agent without an explicit pin (33 of 35 in the retained artifacts: `codex-artifacts/project-a/baked.json` has only `gsd-code-fixer` and `gsd-executor` non-null). An agent whose `.codex/agents/gsd-<x>.toml` was never generated gives `baked.get(agent) is None == expected`, so it is reported as equal. The `"missing file"` label is only reached when the promise is non-null. The new test asserts this behavior: `_baked_mismatches(baked, {..., "gsd-extra": None}) == []`, where `gsd-extra` has no TOML.
**Failure scenario:** a gsd-core release stops emitting TOMLs for some agents, or the install is partial. Step 7 still prints `35 agents; all equal`, and EVAL-04 evidence would show planned == baked for agents that are not installed.
**Fix:**
```python
def _baked_mismatches(baked, promised_map):
    return [
        [agent, "missing file" if agent not in baked else str(baked[agent]), str(expected)]
        for agent, expected in sorted(promised_map.items())
        if agent not in baked or baked[agent] != expected
    ]
```
Change the test so that `gsd-extra: None` with no file is a mismatch.

### WR-02: the matrix mixin is collected as a test class, so the claude matrix runs twice

**File:** `tests/test_ai_kit_gsd_curated_config_matrix.py:19` (`class _ResolveModelMatrixMixin(unittest.TestCase)`)
**Issue:** The pyright fix (2619290) made the mixin subclass `unittest.TestCase`. The unittest loader collects every `TestCase` subclass in the module namespace, whatever its name. I confirmed this: the loader yields `TestResolveModelMatrix`, `...Codex`, `...Opencode` **and** `_ResolveModelMatrixMixin` (HOST = "claude"). That is why the gate records `Ran 36 tests` = 4 x 9. The summary's own split, "9 + 9 + 9, module total 36", does not add up (27 is not 36), and 20-02 recorded 27. The fourth class repeats the full real-node claude matrix in `setUpClass`: 12 real applies and about 420 resolve-model calls against the real HOME. The cost is doubled for no extra coverage, and the gate's test count is wrong.
**Fix:** keep the type-checker happy without making the mixin collectable:
```python
if TYPE_CHECKING:
    _Base = unittest.TestCase
else:
    _Base = object
class _ResolveModelMatrixMixin(_Base): ...
```
Or skip the base class itself in `setUpClass` (`if cls is _ResolveModelMatrixMixin: raise unittest.SkipTest("mixin")`). Then correct the 20-04/05/07 gate counts.

### WR-03: `_toml_semantic_sha` crashes on any TOML date or time value

**File:** `tests/gsd_curated_eval.py:279`
**Issue:** `tomllib` returns `datetime`/`date`/`time` objects for TOML datetimes, and `json.dumps(data, sort_keys=True)` raises `TypeError`. Only `OSError`/`TOMLDecodeError` are caught. I reproduced it: a `config.toml` containing `[notice] seen_at = 2026-10-18T09:00:00Z` raises `TypeError ... when serializing dict item 'notice'`.
**Failure scenario:** if `~/.codex/config.toml` ever holds a timestamp, `run_smoke` dies at `before = snapshot(...)` before any step runs. `snapshot --out/--check` crashes, and so does `setUpClass` of all four matrix e2e classes. Each fails as a traceback, not as a recorded step.
**Fix:** `hashlib.sha256(json.dumps(data, sort_keys=True, default=lambda v: v.isoformat()).encode())`, plus a test with a datetime value.

### WR-04: the local install inherits env overrides that bypass the throwaway HOME (D-09)

**File:** `tests/gsd_curated_eval.py:4067-4074`
**Issue:** the installer env is `{**_project_env(ctx), HOME, XDG_*}`, and `ctx.env` is `{**os.environ, ...}`. gsd-core reads its locations env-first. `.claude/gsd-core/bin/lib/runtime-homes.cjs:392-405` documents `GSD_HOME` as "a WRITE surface" read by `bin/install.js` (`$GSD_HOME/.gsd/defaults.json`) and `GSD_AGENTS_DIR` as env-first. The capability registry resolves `CODEX_HOME`, `OPENCODE_CONFIG_DIR`/`OPENCODE_CONFIG` and `CLAUDE_CONFIG_DIR` before HOME (`capability-registry.cjs:525,1141,2925`). None of these is removed.
**Failure scenario:** a session that exports `GSD_HOME` (or `CODEX_HOME`, or `OPENCODE_CONFIG_DIR`) runs the smoke. `writeNonClaudeDefaults` then rewrites the real `$GSD_HOME/.gsd/defaults.json`. The snapshot guard only hashes `<HOME>/.gsd/defaults.json`, so the write is not detected and the evidence still says `protected set unchanged: pass`. This did not happen on this machine: neither recorded host env list contains these names.
**Fix:** drop every location override from the installer env, for example:
```python
_INSTALL_ENV_DROP = ("GSD_HOME", "GSD_AGENTS_DIR", "CODEX_HOME", "OPENCODE_CONFIG_DIR",
                     "OPENCODE_CONFIG", "CLAUDE_CONFIG_DIR")
env = {k: v for k, v in _project_env(ctx).items() if k not in _INSTALL_ENV_DROP}
```
A better option is to build the env from an allowlist (the `CELL_ENV_KEEP` pattern), and assert in the test that these keys are absent.

### WR-05: the smoke evidence's "Local install" section is printed from constants

**File:** `tests/gsd_curated_eval.py:4826-4838` (rendered at `:4719-4732`)
**Issue:** `_cmd_smoke` hardcodes `local_install = {"scope": "local", "root": "<scratch-a>/.{host}/gsd-core", "version": pinned}` and `install_roots = [...]`. These values are written whatever happened. The real check is in `_inventory` (`:4121-4133`), but the rendered section reads the same when an install failed. On `--host claude`, where there is no local install (a symlink), it wrongly prints `scope: local` and `root: <scratch-a>/.claude/gsd-core`, and `idempotent re-install: no` (the post step returns early without setting `state["idempotent"]`). `20-INTERACTIVE-CODEX.md` step 3 asks the user to confirm `scope: local`, a check that cannot fail. Under AGENTS.md's certainty rule, a constant shown as evidence is an overclaim.
**Fix:** have the install step and `_inventory` return the observed `gsd_core` record (path label, scope, version), store it in `state`, and render from it. Print `not applicable` on claude and `not observed` when the step failed. Add a `_cmd_smoke` render test (there is no `smoke` CLI test at all).

### WR-06: the gitignore note has a tautology and a false or unobserved claim

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:235-245`
**Issue:** the rendered codex note (I ran it) reads: `... .codex/gsd-*.json (.codex = .codex); never ignore the whole directory (opencode writes its own .codex/.gitignore there)`.
1. `({host_dir} = {host_dir})` is a meaningless placeholder.
2. On codex it says opencode writes `.codex/.gitignore`, which is false.
3. On opencode, the claim that opencode writes `.opencode/.gitignore` is not supported by the Phase 20 evidence. `_generated_paths` (`gsd_curated_eval.py:4281`) explicitly looks for `.{host}/.gitignore`, and neither raw smoke output (`tmp/p20/headless/{codex,opencode}-smoke.md`) lists one.

`test_gitignore_prefix_note_is_only_for_non_claude_hosts` checks none of this.
**Fix:** remove the parenthetical. Make the "never ignore the whole directory" reason host-specific: for opencode, a sourced statement ("opencode keeps its own files in `.opencode/` (D-12, not observed in the Phase 20 smoke)"); for codex, the absolute `gsd-core/` path baked into the TOMLs. Assert the codex note does not contain "opencode".

### WR-07: the installer and root notes claim verification of something the smoke did not run

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:227-232, 255-261`
**Issue:** the smoke ran the cached 1.17.0 `install.js` with `--{host} --local --no-legacy-cleanup` under an isolated HOME (`gsd_curated_eval.py:4075-4082`). The product's follow-up runs `installer_argv` (`followups.py:47-57`): `npx ... --<host> --local`, with no `--no-legacy-cleanup`, against the real HOME, for whatever version the target pins. The shipped argv's documented global side effects (`_disclosures`: rewrites `~/.gsd/defaults.json`, scans home host dirs) were therefore never exercised. Yet the codex note says "the --codex --local flags were verified". The opencode note says "the local install root <project>/.opencode/gsd-core was verified", naming a path in the user's project that does not exist yet. Neither note says the evidence is for gsd-core 1.17.0 only.
**Fix:** scope both notes, for example: "the `<project>/.<host>/gsd-core` layout was observed with gsd-core 1.17.0's installer run with `--no-legacy-cleanup` under a throwaway HOME (Phase 20 smoke); this argv (no `--no-legacy-cleanup`, real HOME) and the npx fetch were not exercised." Update `test_phase_20_evidence_notes_are_explicitly_verified` to match.

### WR-08: smoke evidence lists every generated path twice, without saying which project it came from

**File:** `tests/gsd_curated_eval.py:4653`
**Issue:** `run_smoke` joins the `generated_paths` of project (a) and project (b) into one flat list. The raw `tmp/p20/headless/codex-smoke.md` lists `.codex/agents/gsd-planner.toml` twice, and `opencode-smoke.md` lists `gsd-planner.md` at lines 87 and 299. A reader cannot tell which project a path belongs to, or whether (b) is missing anything that (a) has.
**Fix:** keep per-label lists (`{"project-a": [...], "project-b": [...]}`) and render one sub-list per project. Alternatively, render the intersection once and list any difference between the two projects.

### WR-09: the committed codex evidence's paths list is not the harness output (outside the 21-file scope)

**File:** `.planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md:100-195` (cited by the `detection.py` and `followups.py` labels)
**Issue:** I diffed it against the raw `tmp/p20/headless/codex-smoke.md`.
- Missing: `.codex/gsd-core/`, every `.codex/skills/gsd-*`, `.codex/gsd-file-manifest.json`, all three `gsd-doc-verifier` files, and the TOMLs for `code-fixer`, `doc-writer`, `eval-auditor`, `intel-updater`, `research-synthesizer` and `roadmapper`.
- Added: a duplicate `gsd-roadmapper.compact.md` and a `.codex/agents/gsd-file-manifest.json` that the harness never produced.

The section is headed "written by the harness inside codex", but it is a lossy hand transcription. Read on its own, it says codex does not install `gsd-core/` locally, which contradicts step 2.
**Fix:** paste the harness file verbatim (or include it by reference) and note any edits. This is evidence, not product code, but the product labels point at this file.

### WR-10: a new unit test depends on the gitignored checkout-local gsd-core

**File:** `tests/test_gsd_curated_eval.py:985-997` (`test_matrix_cli_opencode_reaches_run_matrix`)
**Issue:** the test mocks `shutil.which` and `run_matrix` but not `gsd_run_reason`, so `_cmd_matrix` still needs a real `.claude/gsd-core/bin/gsd-tools.cjs` on the 1.16/1.17 line. `.claude/` is gitignored (`.gitignore:8`). With `GSD_TOOLS_PATH` patched to a missing file, I got `AssertionError: 3 != 0`. The test it replaced returned before that guard.
**Failure scenario:** a fresh clone, a CI job, or a container without a local GSD install fails the `unit` tier.
**Fix:** `mock.patch.object(ev, "gsd_run_reason", return_value="")` in the test, or pass `--tools` pointing at a temp file plus a patched `gsd_core_version`.

### WR-11: a pre-existing test reads the real `~/.config/ai-kit/review-spec.toml`

**File:** `tests/test_ai_kit_spec.py:5860-5894` (`TestTimeoutTiers.test_resolve_timeout_tiers_cli_subcommand_falls_back_to_policy_default`)
**Issue:** this is the read seen in the `tests.test_ai_kit_spec` output. It is **pre-existing**: added in 052ef0e (2026-09-01), not changed by Phase 20. I confirmed it without touching the real file. I ran the module under a temp HOME seeded with a sentinel global `review-spec.toml`, and only this test printed the sentinel's path (`legacy reviewer fields loaded in memory ...`). It calls `main(["resolve-timeout-tiers", "--cwd", d, ...])` with only the local config isolated, so the global layer is merged from the real `$HOME`/`$XDG_CONFIG_HOME`.
**Failure scenario:** the test reads uz's real config (an AGENTS.md test-isolation violation). If that config sets `[policy]` timeout tiers, the assertion `"600,1200,1800"` fails, depending on the machine.
**Fix:** wrap the call in `mock.patch.dict(os.environ, {"HOME": d, "XDG_CONFIG_HOME": os.path.join(d, ".config")})`, or patch the global-config path resolver, as the neighboring tests that print `/tmp/.../.config/ai-kit/review-spec.toml` already do.

### WR-12: 29 compact opencode agents have no baked model and are never compared

**File:** `tests/gsd_curated_eval.py:4241-4265, 4392-4396`
**Issue:** `_baked_models` globs `gsd-*.md`, so it also reads `gsd-<x>.compact.md` (stem `gsd-<x>.compact`). The retained `opencode-artifacts/project-a/baked.json` has 64 entries: 35 with a model and 29 `*.compact` entries with `null`. `promised_map` only covers the 35 `MODEL_PROFILES` agents, so the compact files are silently ignored. The evidence still says `35 agents; all equal`. If GSD runs a compact variant on opencode, that agent uses opencode's default model, not the plan's.
**Fix:** report the compact variants explicitly ("29 compact agent files carry no `model:` line; not compared"). Better, compare each `gsd-<x>.compact` against `gsd-<x>`'s promise, or record that gsd-core does not bake compact variants as a known limit on the D-07 chain.

## Info

### IN-01: the codex labels start with the same "live-verified" token as fully verified ones

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:52-61, 240-245`
**Issue:** the wording is qualified ("via a headless codex exec 0.162.1 ... TUI confirmation pending"), so it is not strictly overclaimed. The evidence is consistent: both names are present in the recorded list, and the runner scrubs `CODEX_VERSION` from the child env, so codex set it. But the leading token matches the 01.2 labels, while the SPEC says headless runs are not EVAL evidence. `test_codex_labels_are_live_verified` locks in the prefix. Consider "headless-verified (Phase 20)" until the TUI run, then promote.

### IN-02: the `--standalone` claims go slightly beyond what was tested

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:272-282`; `skills/ai-kit-gsd-curated-config/references/runner.md:12-16`; `cross_ai.py:181-184`
**Issue:**
- The comment still says "opencode 2.0.29 run --help formulas", but `--standalone` was only observed on v2.0.31.
- "never inside the user's long-lived managed service" comes from what the flag is meant to do. It was not observed: the smoke only noted no port conflict.
- `resume` (`--session <sid>` plus `--standalone`) is neither in the self-test nor exercised live.
- `OPENCODE_EFFORT_EFFECT` extends one `#high` probe on v2.0.31 to "opencode 2.x".
- There is no version gate if an opencode 1.x binary is on PATH.

Scope each statement to v2.0.31, and add a resume argv assertion to the self-test.

### IN-03: user-facing notes cite planning files that do not ship

**File:** `followups.py:230, 258`; `cross_ai.py:182`
**Issue:** the notes reference `20-SMOKE-OPENCODE.md`/`20-SMOKE-CODEX.md`. These live in ai-kit's `.planning/`, not in the installed skill or the target project. Cite "ai-kit Phase 20 smoke" plus the versions instead.

### IN-04: the smoke's resolve-model step runs with `GSD_RUNTIME=<host>` set

**File:** `tests/gsd_curated_eval.py:4409, 4571` (via `_project_env`, which keeps `GSD_RUNTIME` from `_cmd_smoke:4799`)
**Issue:** a real host session does not export `GSD_RUNTIME`. With it set, this step does not show that the project's managed `runtime` key (D-08) steers `resolve-model` on its own. `validate_applied` does read the key back, so the risk is low. Running this step with `GSD_RUNTIME` removed would make it test what D-08 intends.

### IN-05: duplication and checks that cannot fail in the smoke steps

**File:** `tests/gsd_curated_eval.py:4379, 4381-4421 vs 4544-4580, 4423/4430, 4591, 4419, 522-528`
**Issue:**
- The planned == baked plus resolve-model block is duplicated between project (a) and project (b).
- `_install_local(...) != install_detail` compares a constant f-string, so it cannot fail; only the tree hash checks anything.
- `state["idempotent"] = True` is assigned twice.
- Project (b) sets `idempotent: True` without any re-install.
- `"resolve-model mismatches: {mismatch}"` drops the agent name.
- `_host_model` rebuilds `_set_entries` inline.

Extract one `_planned_vs_baked(ctx, project, plan_path)` helper and reuse `_set_entries`.

### IN-06: test nits

**File:** `tests/test_gsd_curated_eval.py` (`test_cursor_config_change_is_strict` docstring); `tests/test_ai_kit_spec_runtimes_table.py:91-92`; `tests/test_curated_config_recommend.py:1675-1680`
**Issue:**
- The cursor test's docstring still calls the codex config a "host-managed tripwire", while the assertion now (correctly) treats it as strict.
- `assertTrue(any(...))` after `assertTrue(all(...))` adds nothing.
- The copied-default check `unsets or (sets and all(...))` passes when any unset exists, even next to a set that still contains the host.

### IN-07: the matrix e2e tier now reads more of the real host config

**File:** `tests/test_ai_kit_gsd_curated_config_matrix.py:21-27` with `gsd_curated_eval.py:300-312`
**Issue:** under the Phase 19 D-08 real-HOME design, the snapshot now parses the real `~/.codex/config.toml` and hashes the `~/.codex/agents` and `~/.config/opencode/{agents,commands}` trees in `setUpClass`. It is a read-only guard, not a fixture, but it reads more real config than before, and WR-03's crash would hit it. Worth recording against AGENTS.md's real-config rule.

### IN-08: the scratch trust-row exemption compares `abspath`, not `realpath`

**File:** `tests/gsd_curated_eval.py:270-276`
**Issue:** if codex writes the trust row under the resolved path (for example `/var/home/...` vs `/home/...` on this Fedora Atomic layout, or a symlinked TMPDIR), the exemption misses it. The result is a false strict failure. This fails safe, but it would be confusing. Normalize both sides with `os.path.realpath`.

### IN-09: `_cached_installer` reads the real home, not `--home`

**File:** `tests/gsd_curated_eval.py:4027-4036, 4794`
**Issue:** it globs `os.path.expanduser("~")/.npm/_npx` and the pnpm dlx cache, ignoring `args.home`. The call site checks `args.host != "claude"` instead of the detected `host`, so a detected claude host still globs. It is harmless (read-only, cache-only), but it is inconsistent with the `--home` seam.

---

_Reviewed: 2026-10-18T10:25:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
