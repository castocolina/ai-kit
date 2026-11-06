# Phase 31: Removals and small defects - Research

**Researched:** 2026-11-06
**Domain:** repo-internal removals, installer path handling, small defect fixes (no external libraries)
**Confidence:** HIGH (every item below was read in the worktree this session; tags are `[VERIFIED: file:line]`; no web research by owner order)

## Summary

All work is inside the tree. Three skills go away with a known reference set (section 1); six test modules lose only
adapter cases (section 3). Two hidden traps found: (a) the R10 guard as written (a test over `.planning/phases/`)
violates the Phase 28 rule that only `make check-dogfood` reads `.planning/`, and the 30.1 SPEC itself fails the
engine today; (b) the existing JS-template drift test parses only `cursor` out of the template, so R13's equality
needs a real block parser.

**Primary recommendation:** five parallel plans (A removals+R2+R9, B R5, C R6+R8, D R7+R14, E R10-R13) then one wave-2
verification plan (R15 judge loops, herdr check). Regenerate listings once at the end of each plan with
`python3 tools/gen_test_groups.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RMV-01 | execute-gsd removed (R1, R2) | sections 1, 3, 4 |
| RMV-02 | opencode-providers removed (R3) + stale-provider report (R5) | sections 1, 5 |
| RMV-03 | mermaid-audit removed (R4) | section 1 |
| RMV-04 | rtk ban (R7) | section 7 |
| DEF-01 | defects R8-R14 | sections 6, 8 |
| JDG-04 | judge bar (R15) | section 10 |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Runtime code stdlib-only; no hardcoded absolute paths in source/tests; English only; scratch HOME tests; `AI_KIT_REFUSE_REAL_HOME=1`.
- Atomic writes for config; logical commits (tests+docs together); no `--no-verify`.
- New/changed SKILL.md passes skill-judge. New `tests/test_*.py` join the `unit` group automatically; e2e/uv/integration modules need the runner's explicit sets.
- No test reads the repo's `.planning/` (arch rule `check_no_planning_reader`, empty exception list); `make check-dogfood` is the only reader [VERIFIED: AGENTS.md Testing section; tests/test_arch.py:1149-1170].
- Structural rules need a `TestArchNonVacuity` counterpart.

## 1. Removal inventory

Commands used: `git -C <wt> grep -n -I -E ... -- . ':!.planning' ':!docs/prds' ':!docs/superpowers'` (hidden files included).
Prefix-only names (`ai-kit-spec-execute`, `ai-kit-spec-execute-superpowers`, `ai_kit_spec_superpowers`) are KEPT.

### 1a. `ai-kit-spec-execute-gsd` / `ai_kit_spec_gsd` / `ai-kit-spec-gsd.py`

Delete whole: `skills/ai-kit-spec-execute-gsd/` (SKILL.md, `ai-kit-spec-gsd.py`, `ai_kit_spec_gsd/{__init__,adapter,cli,cross_ai_guidance,gsd_config,gsd_cross_ai}.py`, `references/{cross-ai-hook-setup,dispatch-notes,resumable-state,session-wake}.md`), `tests/test_ai_kit_spec_gsd.py` (2600+ lines; adapter only; its `TestDetectFramework`, `TestUntrustedLocalExecuteEntry`, `TestGsdPurposeFilterInertness` handled in section 3).

Delete line / entry:
- `README.md:38` (table row).
- `pyproject.toml:124` (`"skills/ai-kit-spec-execute-gsd",` in pyright `extraPaths`).
- `tests/test_gate_scope.py:38` (`skills/ai-kit-spec-execute-gsd/.*|` alternative in `PRE_WIDEN_RUFF_FILES`).
- `tests/test_arch.py:1311` (`_PHASE25_SKILLS` entry); `:1315` (`_PHASE25_LADDER_PKGS` -> keep only `"ai_kit_spec_superpowers"`); `:1607-1627` (six allowlist keys); `:1680-1688` (six `_CROSS_SKILL_FROZEN` keys; both lists must change together); `:3083` non-vacuity string `from ai_kit_spec_gsd.cli import write_resumable_state` -> swap to `from ai_kit_spec_superpowers.cli import write_resumable_state` (still flagged by `check_wake_isolation`).
- `tests/test_ai_kit_spec_runtimes_table.py:811` (REWRITTEN), `:831` (REFERENCES `dispatch-notes.md`), `:837` (`_EXEC_SKILLS`). PITFALL: `PAIR_RULE_SKILLS = [path for path in REWRITTEN[:4] if "execute-superpowers" not in path]` (line ~820). After removing gsd (index 3) and providers (last), `[:4]` would pull in `curated-config` and demand the pair-rule paragraph there. Change the slice to `[:3]` (review, config, superpowers) or derive explicitly.
- `tests/test_quota_policy_text.py:17-18` constants, classes `GsdExecuteSkill` (:105-124) and `GsdExecuteSkillGuards` (:126-153); keep `SuperpowersExecuteSkill` and others.
- `tests/test_cross_ai_skill_text.py:58` (`LINKING` tuple entry).
- `tests/test_ai_kit_spec_gsd_tools.py:79-88` (`test_skill_md_lists_project_local_roots_first_in_resolver_order`, reads execute-gsd SKILL.md) and `:203-212` (`test_prior_value_shapes`).
- `Makefile:12`, `.pre-commit-config.yaml:15`, `.pre-commit-config.yaml:71` (generated; section 2).

Reword (comment/docstring/prose naming the deleted skill; keep code):
- `skills/ai-kit-spec-execute/SKILL.md:3` (description: "adapter (ai-kit-spec-execute-gsd or ai-kit-spec-execute-superpowers)"), `:58` (`"gsd"` -> delegate to `ai-kit-spec-execute-gsd`: becomes "hand the plan to `/gsd-execute-phase`"), `:79` (anti-pattern sentence about the adapter writing `.planning/` state).
- `skills/ai-kit-gsd-curated-config/SKILL.md:128, 231, 234-235` (hook mentions; `:235` also names `--no-preamble --prepend-file`/guidance), `:352` (ensure-runner row), `skills/ai-kit-gsd-curated-config/references/runner.md:31-32, 66`.
- Docstrings: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py:4-5`, `.../model_detect.py:8`, `tests/test_ai_kit_gsd_curated_config.py:474`, `skills/ai-kit-session-wake/ai-kit-session-wake.py:4`, `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:2,11`, `.../dispatch_injection.py:166,171`, `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:2`, `.../gsd_tools.py:11` (the test file it cites stays).
- `tests/test_ai_kit_spec_e2e.py:1,14,17` (docstring, sys.path, `cli` import).
- KEEP as history with reason: `tests/fixtures/archived/26/26-OWNER-CAPTURES.md:19` and `tests/fixtures/archived/26/skill-judge/check_verdicts.py.txt:8,16` are frozen copies of archived planning data pinned by an arch rule. The SPEC acceptance exempts only `.planning/`, `docs/prds/`, `docs/superpowers/` -> see Open Question 2.

### 1b. `ai-kit-opencode-providers` / `ai_kit_opencode_providers`

Delete whole: `skills/ai-kit-opencode-providers/` (SKILL.md, `ai-kit-opencode-providers.py`, `ai_kit_opencode_providers/{__init__,atomic_write,cli,config_paths,cross_reference,jsonc_edit}.py`), `tests/test_ai_kit_opencode_providers.py`.
Delete line: `README.md:40`, `pyproject.toml:113`, `tests/test_gate_scope.py:39` (`skills/ai-kit-opencode-providers/.*|`), `tests/test_ai_kit_spec_runtimes_table.py:813` and comment `:816`, Makefile/pre-commit generated lists (`tests.test_ai_kit_opencode_providers`).
Reword origin comments (keep code): `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py:6`, `.../raw_store.py:34`, `tools/config_doctor_readers.py:89,109,123,140`, `tools/config_doctor_appliers.py:30,148`, `tools/setup.py:1881`.
Not a hit (keep): `_PRIVATE_DIR_PREFIX = "ai-kit-opencode-probe-"` (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:766`) and its tests `tests/test_ai_kit_spec.py:10653,10678`; `skills/ai-kit-gsd-curated-config/SKILL.md:337` ("opencode providers" row is about config providers, not the skill).

### 1c. `mermaid-audit` / `mermaid_audit` / `test_mermaid_style`

Delete whole: `skills/mermaid-audit/` (SKILL.md, template.md, evals/{fixtures,gold.json,judge-protocol.md,score_consensus.py}, examples/*, references/palettes.md, scripts/{audit_mermaid.py,audit_mermaid.sh,mermaid_style.py}), `tests/test_mermaid_style.py`.
Delete line: `README.md:31`, `pyproject.toml:133` and `:137` (`skills/mermaid-audit/scripts`), generated lists.
Reword: `skills/markdown-to-pdf/scripts/render_mermaid.py:5` (docstring "from skills/mermaid-audit/scripts/audit_mermaid.py — the canonical origin").
HIDDEN HIT the SPEC missed: `.claude-plugin/plugin.json:3` description says "a Mermaid diagram auditor" (case-sensitive grep misses it) -> remove the clause.
HIDDEN DEPENDENCY: `tests/test_run_unittest_parallel.py:47, 52, 182` use `tests.test_mermaid_style` as the "fast real module" fixture (`"1/1 modules passed"`). Replace with another small kept module (e.g. one with a stable sub-second run; pick and verify) in the same commit.
Not hits (keep): `skills/ai-kit-gsd-curated-config/skill_affinity.json:115` (`mermaid-diagrams`, other skill); `docs/wizard-redesign/*` (`mermaid-diagram-specialist`).

### 1d. Surfaces checked with no hit
`.gitlab-ci.yml`, `agents/`, `cursor-agents/`, `examples/`, `tools/hooks/`, `tools/staged_mapper.py`, `tools/run_unittest_parallel.py` (outside generated listings), `tests/fixtures/cross_ai_selftest_secs.json`, wizard catalog (skills are enumerated from disk by `enumerate_entries`), 30.1 patch and tool advisor (no removed skill names; verified by `rg` over `diff-30.1.patch` and `tests/test_tool_advisor*`). No GitHub workflow exists (`git ls-files` shows only `.gitlab-ci.yml`). `evals`: only `mermaid-audit/evals` (no `evals.json`, deleted with the folder).

## 2. Generated listings

- Blocks: `Makefile:7-13` and `.pre-commit-config.yaml:10-16` between `# BEGIN GENERATED test groups` / `# END GENERATED test groups`, plus every hook `entry:` trailing module list (e.g. `.pre-commit-config.yaml:71`) [VERIFIED: grep `BEGIN GENERATED`].
- Producer: `tools/gen_test_groups.py` runs `tools/run_unittest_parallel.py --list-groups` (discovers `tests/test_*.py`; explicit sets in the runner). Regenerate: `python3 tools/gen_test_groups.py`. Check: `tests/test_gate_scope.py::test_generated_listings_name_every_discovered_module` (hint text "stale listing; run: python3 tools/gen_test_groups.py") [VERIFIED: tools/gen_test_groups.py:1-8; tests/test_gate_scope.py:525-536].
- Manual, not generated: `E2E_RECORDED_SECS` and `E2E_MODULES` in `tools/run_unittest_parallel.py:107-177`; `SHARED_MACHINERY` (:181) is pinned by `test_shared_machinery_is_pinned`. Editing the runner file stages "full unit+arch" at commit; avoid new e2e modules (below).
- `tests/fixtures/cross_ai_selftest_secs.json` and the staged_mapper index need no change (the index is rebuilt per commit).
- Rule for parallel plans: only these three generated spots may merge-conflict; after any rebase/merge, re-run the generator (never hand-merge the long lines).

## 3. D-13 case fates

| File | Case / lines | Fate | Covered by kept test |
|------|--------------|------|----------------------|
| `tests/test_ai_kit_spec_trust.py` | `sys.path` insert `:16-17`; `test_gsd_cli_exits_2_on_malformed_local` `:437-447` | delete both | `test_review_spec_main_exits_2_on_malformed_local` and `test_superpowers_cli_exits_2_on_malformed_local` (same file) |
| `tests/test_ai_kit_spec_legacy_config.py` | `sys.path` `:12`; `TestLegacyAdapters.test_gsd_uses_legacy_native_alias_independent_of_host` `:435-446`; `test_gsd_explicit_claude_runtime_model_id_is_not_an_alias_tier` `:448-455` | delete (adapter-only `tier` field logic in `adapter.assemble_candidates`) | `test_superpowers_keeps_the_stored_runtime_for_the_route_walk` stays; shared `normalize_legacy_entry` covered by `TestLegacyNotes` etc. |
| `tests/test_cross_ai_runner_e2e.py` | `TestGsdHookE2E` `:850-926` (uses `gsd_cli.print-dispatch-guidance`, `ensure-runner --guidance-file -`, `build_cross_ai_command`) | delete the class; check helpers (`pids_with_cwd_under`, `write_fake_opencode`) still used elsewhere | runner behaviour is covered by `TestRouteFlagE2E` and the 8 self-test shards; GSD `run-with-timeout` driving a hook string is no longer shipped |
| `tests/test_ai_kit_spec_e2e.py` (e2e, `E2E_MODULES:113`, recorded 1 s) | `import cli` + sys.path `:14,17`; `test_previous_value_contract_on_real_gsd_core` `:66-100` | keep, drop the 3 `prior_value` asserts (:77, 83, 89); keep config_set/config_get/unknown-key asserts (only real-gsd-core test of those shared helpers) | itself |
| same | `TestRealGsdConfigSet.test_write_workflow_keys_round_trip...` `:102-148` (calls `cli.main(["write-workflow-keys"...])`) | rewrite to call `gt.config_set(tools, scratch, "workflow.cross_ai_execution", True, ...)` directly, keep the on-disk assertion | itself (moves to the kept `gsd_tools` caller) |
| same | `TestRealGsdRunsStayInTheirTempRoot` | keep | itself |
| `tests/test_arch.py` | allowlist/frozen/`_PHASE25_*` entries, non-vacuity string | see 1a | - |
| `tests/test_ai_kit_spec_gsd_tools.py` | `:79-88` SKILL.md root-order test; `:203-212` `prior_value` | delete (doc pin of a removed doc; removed function) | `test_gsd_core_roots_project_local_first_then_host_homes` `:71-77`, `tests/test_curated_config_inventory.py:284` |
| `tests/test_ai_kit_spec_runtimes_table.py` | list entries | see 1a | - |
| `tests/test_quota_policy_text.py` | `GsdExecuteSkill`, `GsdExecuteSkillGuards` | delete | `SuperpowersExecuteSkill`, `ReviewSkill` cases, `tests/test_cross_ai_skill_text.py` |
| `tests/test_cross_ai_skill_text.py` | `LINKING` entry `:58` | delete entry | - |
| `tests/test_ai_kit_spec_gsd.py` (deleted) `TestDetectFramework` `:1549-1561` | delete | `tests/test_ai_kit_spec_superpowers.py:2280-2318` (`router_detect_framework`, includes the `"gsd"` marker cases) |
| same `TestUntrustedLocalExecuteEntry` `:1996-2026` | delete | `tests/test_ai_kit_spec_superpowers.py:2338 test_untrusted_local_execute_entry_absent_until_trusted` |
| same `TestGsdPurposeFilterInertness` `:1965-1993` | MOVE (reword, drop GSD wording) to `tests/test_ai_kit_spec_superpowers.py` or next to `tests/test_ai_kit_spec.py:3350`: `execute_selection.resolve_execute_candidates` keeps an untagged candidate and drops a `purpose="review"` one; no other direct test (only comments reference it) | - |
| same `TestKnownGsdRuntimes`, `TestReadGsdConfig`, `TestApplyChanges*`, `TestUndoLog`, `TestWorkflowKeys*`, `TestCli*`, `TestSessionWakeStep`, `TestResumableStateBlock`, skill-text classes | delete (adapter/SKILL only) | - |

New pin required by R1: `tests/test_ai_kit_spec_execute_router.py` (new, unit): the `"gsd"` bullet in `skills/ai-kit-spec-execute/SKILL.md` contains `/gsd-execute-phase` and no `ai-kit-spec-execute-` adapter name; the description names `/gsd-execute-phase`. `detect_framework` still reports `gsd` (already pinned at test_ai_kit_spec_superpowers.py:2291, 2318).

## 4. R2 guidance code

- `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:33` `PROJECT_GUIDANCE_PATH = ".planning/scripts/cross-ai-guidance.md"` (keep line 32 `PROJECT_RUNNER_PATH`); `:185` `def project_runner_command(spec: RunnerSpec, *, guidance: bool = False)` and `:195-196` (`if guidance: tokens += ["--no-preamble", "--prepend-file", PROJECT_GUIDANCE_PATH]`). Remaining callers after removal: `cross_ai_build.py:114` (no guidance arg) and `tests/test_ai_kit_spec_runner_dispatch.py`.
- Tests: `tests/test_ai_kit_spec_runner_dispatch.py:153-160` (guidance case), `tests/test_curated_config_script.py:68-72` (drop the `GUIDANCE_PATH == PROJECT_GUIDANCE_PATH` line, keep runner path), `:447-508` (`test_upgrade_tracer`: rewrite runner-only; lines 457-462, 469-480 are guidance), delete `:632-661` (2 guidance tests), `:710-728`, `:730-739`, `:741-749`, `:751-759` (guidance error cases).
- curated-config `cross_ai_script.py`: `:21-25` `GUIDANCE_PATH`, `GUIDANCE_HEADER_RE`, `_GUIDANCE_NOTICE` (:25-27); `:303-313` `_guidance_bytes`; `:316-318` `plan_guidance`; `:349-352` `_guidance_step`; `ensure_runner(project_dir, guidance_text=None)` `:404`, `_ensure_runner_plans` `:355-376`; `_plan_rendered` (`:194`) stays (runner uses it, `:212`). `cli.py`: `_read_guidance_file` `:218-222`, `_cmd_ensure_runner` guidance branch `:228-235`, `--guidance-file` `:785`. Output keys today `{ready, runner, guidance, notes}` (`cross_ai_script.py:372-376`); SPEC says "keeps its other keys" -> drop `guidance` (also from the error dicts `:332`, `cli.py:233`, `SKILL.md:352` row, and tests `test_curated_config_script.py:462,638,656,726`). Decide in plan: dropping the key is the clean reading.
- `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:289-303` `prior_value` (only caller was `ai_kit_spec_gsd/gsd_config.py:126`).
- Docs: curated-config SKILL.md `:235, :352`; `references/runner.md:31-32, 66`. Template version pin: `tests/test_curated_config_script.py:61 test_template_version_constants_match_the_shipped_template` stays and proves the template is unchanged. Do NOT touch `skills/ai-kit-spec-review/references/cross-ai.mjs`.
- Acceptance search covers `skills/ tools/ tests/`: `rg -n 'PROJECT_GUIDANCE_PATH|guidance=True|--guidance-file|cross-ai-guidance.md|prior_value'` must be empty. Note the `tests/test_ai_kit_spec_superpowers.py` `guidance=None` hits are a different thing (dispatch guidance) and stay.

## 5. R5 check-providers design inputs

- Port from `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py` (read in full): three sources in order local `./.aikit/review-spec.toml`, global `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml` (inactive when local `strategy = "local-only"`; reason text `'local review-spec sets strategy = "local-only"'`), cached catalog `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/spec/model-catalog.json`. Status words `scanned` / `scanned-inactive` / `absent`; audit line `cross-reference: <path> <status>`; warning `warning: "<provider>" is referenced in <path>: <locator> <field>=<value>` + ` (not active: <reason>)` [VERIFIED: cross_reference.py:97-177; cli.py:41-61 of the providers skill]. NEW matching rule (SPEC): match the `provider` part of an opencode reviewer's `provider/model` id and a catalog entry's `provider`; do not substring-match `runtime`/`cli` as the old scan did. Old scan used `provider_id in value` (substring) - do not port that.
- Reuse (no new loaders): `ai_kit_spec/config_io.py` `cfg_local_path`(:263), `cfg_global_path`(:289), `cfg_load_toml`(:309), `cfg_read_bytes`(:329), `cfg_parse_toml_bytes`(:339); `ai_kit_spec/model_catalog.py` `cache_catalog_path`(:54), `CATALOG_META_KEY = "_meta"`(:18), `split_catalog_meta`(:78) (skip `_meta`).
- Served providers: `ai_kit_spec/detection.py` `detect_opencode_models(binary, run_fn=subprocess.run, env=None)` `:297` (runs `[binary, *_list_argv("opencode")]` through `_run_opencode` `:804` -> private cwd, `_probe_env()`; returns list of `provider/model` lines, `None` on failure, `[]` possible) and `detect_installed_clis` `:205` for the binary. Provider = text before first `/`. Fake with `run_fn` seam (tests never run real opencode; tripwire PATH).
- Subcommand table: `skills/ai-kit-spec-review/ai_kit_spec/cli.py` parser registration `_register_*_parsers` (`detect-runtimes` at :148), `_COMMANDS` dict `:990-1013`, handler signature `(args, deps)` with `CliDeps` (`which_fn`, `run_fn`, `env_fn`) `:120-137`. cli.py is 1031 lines: put logic in new modules (`provider_check.py`, `jsonc_read.py`), only parser+handler in cli.py. Exit 0 whatever found (D-02).
- JSONC drift test target: `tools/config_doctor_readers.py` functions `strip_jsonc_comments`(:106), `strip_trailing_commas`(:137), `read_jsonc_checked`(:179), `get_nested`(:201), `_classify`(:86), `code_indices`(:120). Drift test imports it from `tools/` (tests may; skills may not) and compares `provider` keys on shared synthetic fixtures (comments, trailing commas, escaped strings, v1 `provider`, v2 `providers`).
- Config files read (D-03): `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-~/.config}/opencode}/opencode.json(c)`, project `opencode.json(c)`, `.opencode/opencode.json(c)`. Mirror `tools/setup.py:resolve_paths` (`OPENCODE_CONFIG_DIR` > `XDG_CONFIG_HOME/opencode`).
- Never read `auth.json`; never print `apiKey`; a test seeds a config with an `apiKey` marker and a scratch `auth.json` and asserts neither marker appears in output.
- spec-config SKILL.md: Step 1 "Detect" `:80-142` (`detect-runtimes` `:83`, `--check-only` branch `:97-134`, non-check `:136-142`); add `check-providers` call after detect in both branches (before the `--check-only` stop at `:133`). Skill has NO `evals/` dir today (only `references/cli-model-selection.md`) -> R15 needs a new `evals/evals.json`.

## 6. R6 / R8 installer

- `tools/setup.py` [VERIFIED by Read]: `PI_SKILLS` `:48-49` (`{"ai-kit-cross-ai","jev-fast-decision","ai-kit-session-wake","ai-kit-commit-fold"}`); `resolve_paths(env)` `:102-` with `home = env.get("HOME", "")` and `install_dir = env.get("AI_KIT_DIR") or os.path.join(env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share"), "ai-kit")` (:115-117); `_is_inside(path, root)` `:1076-1079` is string-only (`path == root or path.startswith(root.rstrip(os.sep) + os.sep)`); `installed_links` `:1082-1100` (uses raw `os.readlink`); `predecessor_candidates` `:1417-1435` also uses `_is_inside`; other `_is_inside` callers `:1279, :2824, :2865`; `stale_link_candidates` `:1349-1365`; `apply_stale_prune` `:1368-1375` (bumps `pruned`, decrements `unlinked`); `prune_stale` `:1378-1400` (its `else:` branch already prints `warn: removing dead ai-kit link {item} (entry removed upstream)` but has NO caller; interactive branch asks `ask_yes_no`); wizard prunes via `stale_link_candidates` + `apply_stale_prune` inside `_make_apply_housekeeping` `:3879-3881, 3967-3974` (keeps its confirm); `_pi_entries` `:1672`; pi link helpers `:1700-1706`; headless: `_headless_paths_and_entries` `:4114`, `_headless_link_skills` `:4133`, `_headless_sync_pi` `:4237`, `cmd_install_headless` `:4480-4577` (comment `:4527-4529` "deliberate omission: no prune_stale ... A future --prune-stale flag plugs in here" must be rewritten). Both `install` and `reconfigure` `--headless` go through `cmd_install_headless` (`main` :4909-4917). `_refuses_real_home` `:4784-4794` resolves with `realpath` already.
- Where to prune: after `_headless_paths_and_entries`, before `migrate_statusline`/linking in `cmd_install_headless`; claude root always, pi root only `os.path.isdir(paths.pi_dir)` and only `skills/` items (as the wizard filters `item.startswith("skills/")` at :3967-3974). Print one warn per link in sorted `cat/name` order, claude before pi. Use `stale_link_candidates` + `apply_stale_prune` (non-interactive path), not `prune_stale`'s `is_interactive(tty)` branch (tty=None headless). A link that vanished between detect and unlink must count as gone (`unlink_one` check).
- R8 design: one helper `_resolved_inside(target_link_path, kit_dir)`: `os.path.realpath` both sides (realpath of a dangling link target resolves parents and keeps the missing leaf, which is what stale detection needs), then component compare (`os.path.commonpath([...]) == kit`) so `ai-kit` is not inside `ai-kit-old`. Use in `installed_links`, `predecessor_candidates`, `:1279, :2824, :2865`, and give `installed_links` the realpath of each link target (relative readlink targets too).
- Kit dir default: in `resolve_paths`, when `AI_KIT_DIR` is unset use the checkout holding the running script: `os.path.dirname(os.path.dirname(os.path.realpath(__file__)))`; XDG default remains only in `tools/install.sh:49` (bootstrap clone). Empty `$HOME`: `home == ""` must fail with a message (add to `main` before writes). Docstring/header edits: `tools/setup.py:18, :104`.
- Existing tests that pin the old default and MUST change: `tests/test_setup.py:883` (`p.install_dir == "/home/u/.local/share/ai-kit"`), `:889-892` (derived paths), `:899-910` (AI_KIT_DIR > XDG_DATA_HOME). Keep: `:989-996` installed_links, `:1224-1280` prune_stale/stale_link_candidates/apply_stale_prune, `:1483` `_is_inside(backups, root)` False, `:4478-4786` wizard housekeeping, `:5178-5253` (mock `prune_stale` in wizard tests), `:1550-1555` pi_dir.
- `tools/install.sh`: LOCAL mode already resolves `INSTALL_DIR` with `pwd -P` and exports it (`:78-80, :289-291`, pinned by `tests/test_install.sh:38-55` "LOCAL clone resolves+exports INSTALL_DIR"); an `AI_KIT_DIR` given in another spelling is exported unresolved (`:49, :290`). Add a post-fetch normalisation (`INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd -P)"` when the dir exists; no `readlink -f`, it is not portable to macOS `/bin`). Keep `tests/test_install.sh` assertions for the one-line install unchanged; shellcheck clean.
- New tests (unit, scratch HOME inside `tempfile`; synthetic symlinked home and kit alias): in `tests/test_setup.py` (real `os.symlink`; call `cmd_install_headless` with an env dict; assert counts `skip_foreign == 0` and the three pi skills `ai-kit-cross-ai`, `ai-kit-session-wake`, `jev-fast-decision` linked); a `python3 <scratch checkout copy>/tools/setup.py install --headless --skills all` subprocess for the "checkout run" case (no `AI_KIT_DIR`). Avoid a new e2e module (it would force editing `tools/run_unittest_parallel.py`, a shared-machinery file and a 30.1 hunk neighbour).

## 7. R7 rtk

- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:106-116` entry `{"id": "R05", ..., "condition": condition_tool_presence("rtk"), "signals": ("rtk","token killer","tool substitution"), ...}` -> delete the dict (id left unused; R04/R06 untouched). "20-rule/20 rules" text: `README.md:41`; `skills/ai-kit-project-rules-agents/SKILL.md:3, :10 (twice), :156`; `.../rule_checker.py:9`; `.../rules.py:1`; `skills/ai-kit-project-rules-makefile/SKILL.md:17`. SKILL.md also: `:37` ("tool presence looks up `rtk`, `graphify`..."), `:65-67` (example finding using R05/rtk -> switch to another rule). Keep `R20` text (`SKILL.md:156`, id unchanged).
- `skills/_shared/ai_kit_rules_common/tool_presence.py:33` `"rtk": shutil.which("rtk", path=search_path) is not None,` -> drop. Tests: `tests/test_ai_kit_rules_common.py:144` (`assertFalse(result["rtk"])`), `tests/test_ai_kit_project_rules_agents.py:130, 176, 204-208 (R05 not_applicable -> assert R05 absent from findings), 552`.
- Config doctor: `tools/config_doctor_checks.py:559-575 read_rtk_cursor_integration`, `:1021-1037` row `id="rtk-cursor-integration"`; `tools/config_doctor_readers.py:16-19` RTK constants, `:211-248 probe_rtk_cursor_hook`. Tests: `tests/test_config_doctor.py:776-940` (fixtures `_VERIFIED_RTK_SHOW`, `_RTK_SHOW_*`, `_rtk_stub_body`, ~6 cases incl. docstring pin `:920`), `tests/test_config_doctor_pty.py:144-158` (rtk stub in a PTY case; keep the case, drop the stub). Row-count assertions: `test_catalog_contains_at_least_twenty_four_rows` (:641), `test_five_sections_twenty_six_rows` (:932, asserts `len(CONFIG_DOCTOR_ROWS) == 26`) -> 25 here (see section 9: 27-1 = 26 after the 30.1 rebase). `test_config_doctor.py` and `_pty` are `integration` group (uv).
- README: `:52` (usage-metrics row lists "rtk session logs": reading history stays; exempt by folder? NO - README is not exempt, so reword to "other CLI session logs"), `:654` (hook paragraph: "which curated `rtk` substitutions" -> "which modern CLI tools"), `:661` (doctor sentence "plus a cross-runtime `rtk`-Cursor-integration check"). AGENTS.md `:128-133` paragraph (also the dead link, R14).
- usage-metrics: SKILL.md rtk lines `:3, 14, 23-24, 90, 109-113, 124, 300` only DESCRIBE reading history; none says install/init/run rtk [VERIFIED: rg output]. SKILL.md need not change (D-01: not judged unless it changes). The whole folder + `tests/test_ai_kit_usage_metrics.py` are exempt (D-06). Add the D-06 SKILL.md check: no `install rtk`, `rtk init`, or `rtk <subcommand>` invocation.
- Old ban to replace: `tests/test_tool_substitution_hook.py:1299-1310 test_no_hook_file_mentions_the_rewrite_tool` (line-lowercase `rtk` regex over `tools/hooks/`). New test (suggest `tests/test_banned_tool_mentions.py`, unit): `git -C <repo root> ls-files`, whole-word case-insensitive `\brtk\b`, UTF-8 `errors="replace"`, skip binaries (NUL sniff), skip with a named reason if not a git work tree; named exemptions with reasons: `.planning/`, `docs/prds/`, `docs/superpowers/`, itself, `skills/ai-kit-usage-metrics/`, `tests/test_ai_kit_usage_metrics.py`; non-vacuity case on a synthetic tracked-file list/temp git repo (also an exempt-path and a non-word `artkit` case). Repo root: `Path(__file__).resolve().parent.parent`.
- Whole-tree remaining hits after the above (non-exempt) are only the ones listed; `tests/fixtures/archived/` has none. `tests/test_ai_kit_spec_goal_prompt*`, `tools/hooks/` have none.

## 8. R9-R14 defects (current lines)

- R9: `skills/ai-kit-gsd-curated-config/SKILL.md:133-135` "candidates are the bare model ids the session provider serves (`PI_PROVIDER`, which `inventory` reads inside a pi session)". Messages (the SPEC says inventory.py; the strings live in two other files): `ai_kit_gsd_curated_config/recommend.py:325` "(PI_PROVIDER is unset; run inventory inside the pi session); plan-unset it" (`:320` also names `PI_PROVIDER`), `plan_io.py:540-541` "(PI_PROVIDER was unset when inventory ran, ...); run inventory inside the pi session, or plan-unset it"; code read `inventory.py:471-474` (comment "pi exports the session provider id to its bash tool"). Tests that must keep matching: `tests/test_curated_config_recommend.py:940 assertIn("PI_PROVIDER is unset", entry["why"])`, `tests/test_curated_config_plan_edit.py:256 assertRaisesRegex(PlanEditError, "PI_PROVIDER.*plan-unset")` - keep those phrases. No eval/golden pins the old sentence (`rg -F 'inside the pi session'` finds only the two sources). Archived guide: `.planning/milestones/v1.3-phases/22-pi-live-validation/22-INTERACTIVE-PI.md` S2 and `.planning/milestones/v1.3-OWNER-FOLLOWUP.md:72` get dated notes; the byte copy `tests/fixtures/archived/22/22-INTERACTIVE-PI.md:93` is pinned by an arch rule - leave. Doc-contract test: SKILL.md says the variables exist only for commands the pi agent runs through its own bash tool, not `!` or RPC bash.
- R10: engine `skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py` (`check <spec> [--engine]`, exit 0 ok / 1 drift / 2 fail closed). Ran it this session over all SPECs (script `tmp/plan-31/research/floor.sh`): 25.1 `ok:false` floor 48 table 47 missing `["encoding","R9"]`; ALSO `.planning/phases/30.1-.../30.1-SPEC.md` `ok:false` floor 47 table 46 missing `["encoding","R3"]`; 28, 29, 29.1, 30, 30.2, 31 are ok. A guard over `.planning/phases/` fails on arrival unless 30.1-SPEC.md gets its `(added ...)` row too (Open Question 1). 25.1 SPEC path: `.planning/milestones/v1.3-phases/25.1-configurable-cross-ai-retry-ladder-and-upstream-error-propag/25.1-SPEC.md` (history folder, edit allowed per SPEC).
- R11: only `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:248-257 _gsd_json` parses gsd-tools output; its callers `:274 (roadmap.analyze), :283 (runtime-identity), :293 (init.phase-op)` all go through it. Other `json.loads` in the skill are not gsd-tools: `gp_host.py:96, 154, 412, 520` (ai-kit-spec/jev output), `:337`, `goal_prompt.py:425` (config file). Add `_load_gsd_reply(out)` (prefix `@file:`, read path, else parse). Tests: fake gsd command in `tests/test_ai_kit_spec_goal_prompt_cli.py` (existing `--gsd-cmd` case `:413`); missing file -> existing `UsageError("the --gsd-cmd roadmap query failed or did not print JSON")` (`:276`).
- R12: `skills/ai-kit-spec-review/ai_kit_spec/routing.py:45-57 host_can_select` docstring: "Verified only for Claude Code aliases on Claude Code. Every other host is session-default-only until Phases 20-22 (R3)." `RUNTIMES["claude"].native_selectors = ("fable","opus","sonnet","haiku")` (`detection.py:113`); test file `tests/test_ai_kit_spec_routing.py`.
- R13 lists: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:49 RUNNER_IDS = ("pi", "cursor", "opencode", "codex")`; `host.py:19 HOSTS = ("claude", "codex", "opencode", "cursor", "pi")`; `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:21-27 HOST_BINARY` (`cursor: "agent"`); `plan_edit.py:374` text "script target {runner_id} is not one of pi, cursor, opencode, codex, is the host, or is not installed" -> build from `RUNNER_IDS`; JS template list: `const RUNTIMES = {` at `cross-ai.mjs:1333` with keys cursor, opencode, pi, codex, claude, copilot (to `};` at :1459). Table `RUNTIMES` (live run this session): runner=True for pi, opencode, cursor, codex, claude, copilot; runner=False grok; claude `review_only`; binaries cursor=('cursor-agent','agent'). Deliberate differences: RUNNER_IDS excludes claude (review-only) and copilot (not a curated runner choice, `tests/test_ai_kit_spec_runtimes_table.py:472` asserts it); HOSTS adds claude, excludes copilot/grok; HOST_BINARY excludes copilot/grok (binary `agent` for cursor). EXISTING TEST IS WEAK: `test_runner_template_keys_use_table_ids` (`test_ai_kit_spec_runtimes_table.py:477-487`) splits on the first `};` and, run this session, extracts only `['cursor']`; the new drift test needs a brace-matched parse of the block (keys at 2-space indent between `:1333` and the closing `\n};`) and equality with `{rid for rid,row in RUNTIMES.items() if row.runner}`. The cursor-agent->agent mapping drift is already partly pinned in `tests/test_run_unittest_parallel.py:570-576`.
- R14: link line is `AGENTS.md:132` (`[CLI Environment](.claude/cli-environment.md)`), `.gitignore:8` is `.claude/`; the other relative link `AGENTS.md:291 docs/run-book/graphify.md` exists. Reuse `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` `_LINK_RE`(:22), `_parse_link_target`(:30, strips `#`/`?`, skips URLs and absolute), `_without_fenced_code`(:~50); add `git check-ignore -q <target>` (exit 0 = ignored) with repo-root cwd; skip with a named reason outside git. Test non-vacuity: temp git repo with ignored file and an AGENTS.md linking it.

## 9. Overlap with Phases 30.1 and 30.2 (orchestrator rebases later)

30.1 patch hunks (`tmp/plan-31/research/hunks.py` over `diff-30.1.patch`), vs Phase 31 edits:
- `README.md`: 30.1 hunk `old 661+7` has the `rtk` doctor sentence as context and adds paragraphs right after "bulk-apply." Phase 31 rewrites that sentence -> text conflict. After rebase: keep 30.1's added paragraphs, delete only the `, plus a cross-runtime `rtk`-Cursor-integration check` clause. 30.1 hunks `70+10`, `111+59` are far from the skill rows (31, 38, 40) and `:41`/`:52`/`:654`.
- `tools/setup.py`: 30.1 `resolve_paths` hunk `old 117+8` (replaces the `state_base`/`backups_dir` lines with `_sibling("config_doctor_appliers").backups_root(env)`) is adjacent to R8's `install_dir` lines (115-117) -> likely conflict; re-apply R8's default-kit-dir change on top of 30.1's text. Other 30.1 hunks (3412-4069 wizard commit/housekeeping at `_make_apply_housekeeping 3931`, `launch_wizard 4004-4069`, `cmd_install 4069`, `cmd_config_doctor 4657`) sit around, not inside, `installed_links`/`stale_*`/`cmd_install_headless`; but `_make_apply_housekeeping` is where the wizard prunes: re-check it still calls `apply_stale_prune` and that R8's resolved-inside helper is used by 30.1's new code paths. `tools/setup.py` header hunk `old 24+6` adds `import functools` near the docstring env list (`:18`) - small.
- `tests/test_setup.py`: 30.1 hunks at 265, 2387-2407, 4047-4089, 4494 (TestWizardHousekeeping start); Phase 31 edits `:883-910` (resolve_paths defaults), new classes. After rebase re-run `python3 -m` the module; `:4494` neighbours prune tests only if they are touched.
- `tools/config_doctor_checks.py`: 30.1 adds ~120 lines at `old 582` (Playwright helpers, right after `read_codegraph_global_sentence`, i.e. directly below the rtk reader `:559-575`) and a new row appended at `old 1053` (end of `CONFIG_DOCTOR_ROWS`, after `codegraph-global-sentence`); Phase 31 deletes `read_rtk_cursor_integration` (:559-575) and the row (:1021-1037). Hunks are adjacent but non-overlapping; resolve by deleting only the rtk function and row. Row count: 30.1 changes `tests/test_config_doctor.py:940` `26` -> `27`; after both, expected `26`. Rename the test `test_five_sections_twenty_six_rows` only if the count word no longer matches.
- `tools/config_doctor_appliers.py` (30.1 hunks `9+14`, `407+9`) vs Phase 31 origin comments `:30, :148` (`:30` is in the 9-22 docstring hunk) -> adjacent; reword the comment inside the rebased text.
- `tests/wizard_fixtures.py` (30.1 hunk `old 55+6/62+17`, diff line 4274): 30.1 adds a synthetic `("hooks", "rtk-hint", False)` item; wizard tests `diff-30.1.patch` lines 1975/1986 (`await pilot.press("down")  # rtk-hint (off)`, `"2/2: tool-advisor, rtk-hint"`) -> the rtk ban fails on all of them. After rebase: rename the fixture item to a neutral name (e.g. `extra-hint`) in `tests/wizard_fixtures.py` and in the wizard tests (`tests/test_wizard_app_*.py`, `tests/test_wizard_hostpane.py` - grep `rtk-hint`), update the `"2/2: tool-advisor, ..."` assertion. Run the ban test after rebase.
- `tests/test_tool_substitution_hook.py` (30.1 hunk `404+7`, class `TestWiring`) vs Phase 31 removal of `:1299-1310` -> far apart.
- `tests/test_arch.py` (30.1 hunk `1841+6`, `_BROAD_EXCEPT_BACKSTOPS`) vs Phase 31 `:1311, 1607-1688, 3083` -> far apart. 30.2 plans 01 and 04 also edit `tests/test_arch.py` (status-line rules; `files_modified`) - separate regions.
- `tests/test_run_unittest_parallel.py` (30.1 hunk `537+6`, DriftTest) vs Phase 31 `:47, 52, 182` -> separate. `tools/run_unittest_parallel.py` (30.1 hunk `96+10`, INTEGRATION_MODULES) - Phase 31 should not edit this file.
- `Makefile` / `.pre-commit-config.yaml` generated lists: always conflict; after rebase run `python3 tools/gen_test_groups.py`.
- 30.2 plan 05 `files_modified`: `tools/setup.py` (segment inventory/`render_preview`/host_keys), `README.md` (Cursor status-line quota part), `tests/test_setup.py`, `tests/wizard_fixtures.py`, wizard tests: no overlap with `resolve_paths`, `_is_inside`, prune, headless, rows 31/38/40/41/52/654/661.
- Does the 30.1 wizard catalog or the Phase 30 tool advisor list the removed skills? No: `rg` over `diff-30.1.patch` and `tests/test_tool_advisor_*.py` for `execute-gsd|opencode-providers|mermaid` is empty; the only rtk hits are the `rtk-hint` fixture items above.

## 10. Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` via `tools/run_unittest_parallel.py` (one subprocess per module; tripwire + baseline env) |
| Config file | runner sets in `tools/run_unittest_parallel.py:92-190`; groups `unit`, `arch`, `unit-uv`, `integration`, `e2e` |
| Quick run | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_x [tests.test_y]` (uv groups: `uv run python tools/run_unittest_parallel.py tests.test_config_doctor`) |
| Full suite | `make test` (+ `make pyright`; `make validate` = commit/push hooks) |

### Phase Requirements -> Test Map
| Req | Behavior | Tier | Test | Command |
|-----|----------|------|------|---------|
| R1 | router `gsd` branch names `/gsd-execute-phase`, no adapter | unit | NEW `tests/test_ai_kit_spec_execute_router.py` | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_execute_router` |
| R1/R3/R4 | no removed names; modules still green | unit+arch | existing edited modules, `tests.test_arch`, `tests.test_gate_scope`, `tests.test_ai_kit_spec_runtimes_table`, `tests.test_markdown_to_pdf`; acceptance `git grep` recorded in verification | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_gate_scope tests.test_ai_kit_spec_runtimes_table tests.test_markdown_to_pdf tests.test_run_unittest_parallel` |
| R2 | no guidance param; `ensure-runner` ready; template unchanged | unit | `tests.test_ai_kit_spec_runner_dispatch`, `tests.test_curated_config_script` (incl. template pin :61) | same runner |
| R5 | stale reviewer/catalog/inactive global/v1+v2/fallback label/not-checked/served; apiKey never shown; JSONC drift vs `tools/config_doctor_readers.py` | unit | NEW `tests/test_ai_kit_spec_check_providers.py`, NEW `tests/test_ai_kit_spec_jsonc_read.py` | same runner |
| R6 | dead links pruned both roots, one warn each; foreign/real/live untouched | unit | `tests.test_setup` new class (scratch HOME) | `python3 tools/run_unittest_parallel.py tests.test_setup` |
| R7 | rtk ban + non-vacuity; R05 retired; no doctor rtk row | unit (+integration) | NEW `tests/test_banned_tool_mentions.py`; `tests.test_ai_kit_project_rules_agents`, `tests.test_ai_kit_rules_common`, `tests.test_tool_substitution_hook`, `tests.test_ai_kit_usage_metrics` (unit); `tests.test_config_doctor`, `tests.test_config_doctor_pty` (integration, uv) | `uv run python tools/run_unittest_parallel.py tests.test_config_doctor tests.test_config_doctor_pty` |
| R8 | alias home/kit: 0 foreign, 3 pi skills linked; checkout run uses its checkout | unit + shell | `tests.test_setup` new class; `bash tests/test_install.sh` | `bash tests/test_install.sh` |
| R9 | wording pinned | unit | NEW doc-contract case (e.g. in `tests/test_curated_config_skills.py` or recommend tests); live herdr check recorded in 31-VERIFICATION.md | runner |
| R10 | 25.1 (and 30.1) pass; guard fails on fixture with a row removed | unit | extend `tools/check_dogfood.py` + `tests/test_check_dogfood.py` (see Open Question 1); alt e2e module needs `E2E_MODULES` + `E2E_RECORDED_SECS` | `python3 tools/run_unittest_parallel.py tests.test_check_dogfood`; `make check-dogfood` |
| R11 | `@file:` read; missing file -> existing error | unit | `tests.test_ai_kit_spec_goal_prompt_cli` | runner |
| R12 | docstring has no "Phase"; names exactly the native-selector runtimes | unit | `tests.test_ai_kit_spec_routing` | runner |
| R13 | all copies equal `RUNTIMES` with listed differences; fails on copy-only runtime | unit | NEW `tests/test_runtime_list_drift.py` | runner |
| R14 | AGENTS.md links resolve and none ignored | unit | NEW `tests/test_agents_md_links.py` | runner |
| R15 | evals shape; judge verdicts recorded | unit | `tests.test_skill_evals_shape` (auto-discovers `skills/*/evals/evals.json`); judge runs by `skill-judge` loop | runner |

### Sampling Rate
- Per task commit: the owning module(s) above (sub-second to a few seconds; no sleeps).
- Per plan end: `make test` then `make pyright`; regenerate listings first (`python3 tools/gen_test_groups.py`).
- Phase gate: `make test`, `make pyright`, `make check-dogfood`, `bash tests/test_install.sh`, then `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] New unit modules listed above (join `unit` automatically; none needs a runner exception set).
- [ ] Runner exception sets only if a new module needs uv/PTY/e2e: none planned. If Open Question 1 is resolved as an e2e module, add it to `E2E_MODULES` (:107) and `E2E_RECORDED_SECS` (:151) in `tools/run_unittest_parallel.py` (a SHARED_MACHINERY file; keep that edit in one plan only).
- [ ] New `evals/evals.json` for `ai-kit-spec-execute`, `ai-kit-spec-config`, `ai-kit-gsd-curated-config` (the latter has `evals/*.md` only, no `evals.json`): rules in `tests/test_skill_evals_shape.py:15-60` (>=5 evals, ids `casual-|precise-|edge-`, keys `id,prompt,expected_output,files,assertions`, no machine paths).

## Security Domain

| ASVS | Applies | Control |
|------|---------|---------|
| V5 Input validation | yes | R5 JSONC/TOML parsers fail soft; R11 `@file:` path read is a local reply from the user's own gsd command (read only, size-capped like `handle.read(1 << 20)`); R6 removes only links whose resolved target is inside the resolved kit dir |
| V6 Cryptography | no | - |
| V7 Error/log handling | yes | R5 must not print `apiKey`/`auth.json` values (test marker) |

Threat patterns: symlink following (R6/R8: use `lstat`/`islink`, unlink the link only, never `rmtree`); path-prefix confusion `ai-kit` vs `ai-kit-old` (component compare); secret leak in diagnostics (R5).

## Don't Hand-Roll

| Problem | Use instead |
|---------|-------------|
| TOML/catalog/path loading for R5 | `config_io.cfg_*`, `model_catalog.cache_catalog_path/split_catalog_meta` |
| Link extraction (R14) | rules-agents `cli.py` `_LINK_RE`/`_parse_link_target`/`_without_fenced_code` |
| `@file:` semantics (R11) | mirror gsd-core `resolveAtFileOutput` (prefix, read, parse) |
| Listing regeneration | `tools/gen_test_groups.py` |
| Unlink/prune | `unlink_one`, `stale_link_candidates`, `apply_stale_prune` |

## Common Pitfalls
1. `PAIR_RULE_SKILLS = REWRITTEN[:4]` silently shifts when entries are removed (section 1a).
2. The weak JS-template regex (section 8 R13) passes with one runtime; the equality test must brace-match.
3. `tests/test_run_unittest_parallel.py` uses `tests.test_mermaid_style` as its sample module.
4. `.claude-plugin/plugin.json:3` mentions "Mermaid diagram auditor" (case).
5. Removing `rtk` from `tool_presence` breaks `result["rtk"]` in `tests/test_ai_kit_rules_common.py:144` and presence dicts in the agents tests.
6. `test_setup.py:883` pins the XDG default install dir; R8 changes it.
7. A `.planning/` reader in tests trips `check_no_planning_reader` (R10).
8. Any hand-merged generated line: always regenerate.
9. ensure-runner key order/`guidance` key: callers print the JSON; update `SKILL.md:352`.

## Assumptions Log
| # | Claim | Risk if wrong |
|---|-------|---------------|
| A1 | Dropping the `guidance` key from `ensure-runner` output is the intended reading of "keeps its other keys" | tiny; callers only print |
| A2 | `execute_dispatch.build_execute_guidance` and similar shared helpers may now have no non-test caller; left in place (SPEC lists the removable code explicitly) | dead code later; vulture (confidence 80) does not flag functions |
| A3 | `os.path.realpath` of a dangling link target resolves parents and keeps the leaf on Linux and macOS | prune detection misses a dead link; covered by the alias test |
| A4 | A neutral replacement module for `tests.test_run_unittest_parallel` samples exists and runs sub-second | choose and time one when planning |

## Open Questions (real blockers)
1. **R10 guard location.** SPEC/D-08 say "a test over every SPEC under `.planning/phases/`, e2e tier". That contradicts the Phase 28 rule (arch rule: no test reads `.planning/`; `check-dogfood` is the only reader; the long-path env has no `.planning/`). Also 30.1-SPEC.md currently fails the engine (`encoding R3`), so a guard fails on arrival. Recommendation: implement the guard in `tools/check_dogfood.py` (already reads `.planning/`, already runs read-only node/gsd-tools via `GSD_TOOLS_REL`; hook is pre-push, part of `make validate`), unit-tested on fixture SPECs in `tests/test_check_dogfood.py` with a row-removed non-vacuity case; add the `(added ...)` row to 30.1-SPEC.md as part of the same plan (it is a one-line history edit). Owner/jev to confirm because D-08 named the e2e tier.
2. **History exemption.** `tests/fixtures/archived/26/*` still names `ai-kit-spec-execute-gsd` (frozen archived copies). Either amend the SPEC acceptance list of exempt paths to include `tests/fixtures/archived/` (recommended; they are history) or rewrite them (breaks the arch pin).

## Suggested plan split (lean, parallel; shared files = generated listings only)
- Wave 1 (parallel):
  - **A removals+R2+R9**: delete 3 skills + tests + list entries + README rows (31/38/40). A owns ALL README edits (rows, `:41` 19-rule, `:52`/`:654`/`:661` rtk wording) so no other plan touches README.md. Also pyproject, gate_scope, arch lists, runtimes_table (also drops the superseded weak registry tests), quota_policy_text, cross_ai_skill_text, plugin.json, run_unittest_parallel sample, guidance code (R2), curated-config SKILL.md/runner.md + R9 wording and recommend.py/plan_io.py, spec-execute SKILL.md + evals + router pin test, new `evals.json` for curated-config. Does not touch `tools/setup.py` or `tools/config_doctor_*` (C and D own the origin-comment rewrites there).
  - **B R5**: `provider_check.py`, `jsonc_read.py`, cli.py wiring, spec-config SKILL.md + `evals.json`, 2 test modules.
  - **C R6+R8**: `tools/setup.py` (+ the `:1881` comment), `tools/install.sh`, `tests/test_setup.py`, `tests/test_install.sh`.
  - **D R7+R14**: rules.py, tool_presence, agents SKILL.md + tests, config doctor rows/readers (+ origin comments `config_doctor_readers.py:89-140`, `appliers.py:30,148`), `tests/test_config_doctor*.py`, `tests/test_tool_substitution_hook.py`, AGENTS.md rtk paragraph + link, new `tests/test_banned_tool_mentions.py`, `tests/test_agents_md_links.py`. No README.
  - **E R10-R13**: `tools/check_dogfood.py` + test, 25.1 and 30.1 SPEC rows, `goal_prompt.py`, `routing.py`, `plan_edit.py`, new `tests/test_runtime_list_drift.py`.
  Each ends with `python3 tools/gen_test_groups.py` (only if it added/removed modules), `make test`, `make pyright`.
- Wave 2: **F verification**: skill-judge loops for `ai-kit-spec-execute`, `ai-kit-spec-config`, `ai-kit-gsd-curated-config` (rules-agents listed as not judged per D-01), herdr pi check (R9), `31-VERIFICATION.md`, final grep acceptance, ship per AGENTS.md.

## Sources
Primary: worktree files read this session (cited by path:line). Scripts: `tmp/plan-31/research/{g1.sh,g2.sh,floor.sh,rt.py,hunks.py}` and outputs `g1.txt`, `g2.txt`. No external sources (owner order); SPEC Background supplies the external facts (pi 1.3.0, opencode 2.0.31).

**Valid until:** until Phase 30.1/30.2 are merged (line numbers in section 9 are relative to this base).
