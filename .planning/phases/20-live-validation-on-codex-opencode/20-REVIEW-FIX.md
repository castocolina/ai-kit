---
phase: 20-live-validation-on-codex-opencode
fixed_at: 2026-10-18T12:30:00Z
review_path: .planning/phases/20-live-validation-on-codex-opencode/20-REVIEW.md
ponytail_review_path: .planning/phases/20-live-validation-on-codex-opencode/20-PONYTAIL-CODE-REVIEW.md
iteration: 1
findings_in_scope: 31
fixed: 28
skipped: 3
status: partial
---

# Phase 20: Code Review Fix Report

**Fixed at:** 2026-10-18
**Sources:** `20-REVIEW.md` (WR-01..WR-12, IN-01..IN-09) and `20-PONYTAIL-CODE-REVIEW.md`
(H1, H2, M1-M5, L1-L8). Overlaps count once: WR-01 = M3, WR-05 = H1, WR-06 = H2, WR-08 = M2,
WR-02 = M4.

**Summary:** 31 distinct findings in scope; 28 fixed (IN-02 and M5 in part), 3 skipped (IN-01;
IN-07, recorded only; WR-09, left to the orchestrator by instruction).
Every WR and every H/M is fixed. Gates and smokes ran in this worktree (the main checkout of
the `gsd/v1.3-curated-config-v2` branch), not in an isolated review-fix worktree.

## Fixed

Red evidence: each regression test below was run against the pre-fix code first and failed.

| Finding | Commit | Regression test (red before the fix) |
|---|---|---|
| WR-03 | 89dafe1 | `TestSnapshot.test_codex_toml_datetime_value_hashes` (TypeError before) |
| IN-08, L5, L8 | 89dafe1 | `test_codex_trust_row_under_resolved_root_is_exempt` (sha differed before); L8: `Namespace(..., scratch_root=[])` in the snapshot CLI tests |
| WR-04, L3, IN-09 | 0d326c5 | `test_install_local_uses_isolated_xdg_paths_and_expected_argv` (GSD_HOME etc. present before), `test_install_local_without_installer_dir_refuses`, `test_cached_installer_picks_pinned_version_in_both_cache_layouts` (read `~` before) |
| WR-04 follow-up | dbcb046 | same install test, now asserting the `process.execPath` probe. Found by the local codex smoke: the allowlist dropped volta's vars, so the shim failed with exit 126 ("Node is not available") |
| WR-01 / M3 | c2c2155 | `test_baked_codex_models_and_mismatch_shapes` now expects `[["gsd-extra", "missing file", "None"]]` (it pinned `[]` before) |
| WR-05 / H1 | c2c2155 | `test_evidence_failed_post_step_never_renders_all_equal`, `test_evidence_on_claude_marks_local_install_and_baked_not_applicable`, `test_evidence_renders_observed_records_and_paths_per_project` |
| WR-08 / M2 | c2c2155 | `test_run_smoke_keeps_paths_and_records_per_project`, `test_generated_paths_omit_the_host_gitignore` |
| WR-12 | c2c2155 | `test_evidence_renders_observed_records_and_paths_per_project` (compact line); the local opencode smoke prints `29 compact agent files carry no model: line; not compared` per project |
| M1, IN-05, IN-04 | c2c2155 | `test_baked_chain_names_every_resolve_mismatch_without_gsd_runtime`, `test_baked_chain_summary_is_per_project` |
| M5, L4, L6 | c2c2155 | `test_project_env_drops_runtime_dir_only_for_non_claude` (L4 case); L6 guard: `test_baked_opencode_models_read_frontmatter_including_compact` (passes before and after: a refactor guard) |
| WR-06 / H2, WR-07, IN-03 | db4cbc5 | `test_gitignore_prefix_note_reason_is_host_specific`, `test_phase_20_evidence_notes_claim_only_what_the_smoke_ran` (both red before) |
| IN-02 (product text) | db4cbc5 | goldens regenerated (`OPENCODE_EFFORT_EFFECT`); runner.md wording scoped to v2.0.31 |
| WR-02 / M4, L7 | b18d148, 21180be | `TestMatrixModuleCollection.test_matrix_module_collects_three_host_classes_only` (the loader found 36 tests and a fourth class `_ResolveModelMatrixMixin` before) |
| WR-10 | f8ba9dc | `test_matrix_cli_opencode_reaches_run_matrix` with `--tools <missing>` (`3 != 0` before) |
| WR-11 (pre-existing) | 8e09ac3, 3e947d2 | run under a temp HOME seeded with a sentinel global `review-spec.toml` (`timeout_tiers = [11, 22, 33]`): `'11,22,33' != '600,1200,1800'` before, OK after. The sibling `..._uses_reviewer_override` test also read the real file; the class `setUp` now isolates both. `tests.test_ai_kit_spec` prints no real-home config path any more |
| IN-06, L2 | 72b9bcf | assertions tightened in `test_curated_config_recommend`, `test_ai_kit_spec_runtimes_table`; docstring fixed |
| L1 | 14bea76 | no behavior change; `tests.test_ai_kit_spec_runtimes_table` green |

Notes on specific fixes:

- **WR-01 / M3, the installer check.** The checkout-local `.claude/gsd-core` has no
  `bin/install.js` (it ships only `gsd-tools.cjs` and its lib). The 1.17.0 installer the smoke
  runs is the cached npx package. Its `installCodexConfig` writes one TOML per source
  `gsd-*.md` with no skip list (`bin/install.js:7203`, write at `7258-7266`). The retained raw
  artifact `codex-artifacts/project-a/baked.json` has all 35 agents. The 6 "TOML-less" agents in
  M3 come from the lossy hand transcription in `20-SMOKE-CODEX.md` (WR-09), not from the
  installer. So no agent is exempt and no `not emitted for codex by gsd-core <version>` list is
  needed: every missing file is a mismatch. The code comment on `_baked_mismatches` cites these
  installer lines.
- **WR-04.** The installer env is now `INSTALL_ENV_KEEP` (= `CELL_ENV_KEEP` + `TMPDIR`) plus HOME
  and the four XDG dirs. The test asserts that `GSD_HOME`, `GSD_AGENTS_DIR`, `CODEX_HOME`,
  `OPENCODE_CONFIG_DIR`, `OPENCODE_CONFIG`, `CLAUDE_CONFIG_DIR`, `XDG_CONFIG_DIRS`,
  `XDG_DATA_DIRS`, `GSD_RUNTIME` and `RUNTIME_DIR` are absent.
- **IN-04.** `_baked_chain` runs project-local `resolve-model` without `GSD_RUNTIME`. Both local
  smokes stayed green, so the managed `runtime` key (D-08) steers `resolve-model` on its own.
- **WR-07 wording.** Both notes now share `_smoke_scope(host)`: "observed in the ai-kit Phase 20
  smoke, which ran gsd-core 1.17.0's cached installer as --<host> --local --no-legacy-cleanup
  under a throwaway HOME; this follow-up's argv (no --no-legacy-cleanup, the real HOME, the
  inventory's version), the shipped npx launcher and its registry fetch were not exercised".
  The codex gitignore reason is "gsd-core 1.17.0's installer merges its block into
  .codex/config.toml (source-inspected)". The opencode reason says the opencode-written
  `.opencode/.gitignore` was not observed.

## Skipped

- **IN-01** (codex labels start with "live-verified"). D-05 says "live-verified", and its
  2026-10-18 outcome keeps both names with headless-evidence labels. The 20-04 Task verify also
  asserts the `live-verified (Phase 20)` prefix. The labels already say "headless codex exec
  0.162.1 ... TUI confirmation pending", so the qualification is visible. Promote or rename
  after the interactive TUI run (20-07 follow-up).
- **IN-02, template part** (the `cross-ai.mjs` "2.0.29"/"2.x" comment and a `resume` argv
  self-test). Any template byte change moves the stamped `sha256` and needs a re-render of the
  tracked `.planning/scripts/cross-ai.mjs`, which is a template-version event and not a small
  change. `--print-argv` also has no resume mode to assert against. The product-facing
  wording (runner.md, `OPENCODE_EFFORT_EFFECT`) is fixed. No version gate for opencode 1.x was
  added.
- **IN-07** (the matrix e2e tier reads more real host config). This is the Phase 19 D-08 real-HOME
  design and a read-only guard. Recorded here against the AGENTS.md real-config rule. WR-03's
  crash path is fixed, so a timestamp in `~/.codex/config.toml` no longer breaks `setUpClass`.
- **M5, the `_promise(agent, plan, tables, host)` unification.** Applied: `_host_model` uses
  `_set_entries`, the dead `elif` in `_mismatches` is gone, and the smoke's third spelling went
  away with M1. Not applied: one shared tier/model helper. `_tier_for` still runs twice per
  agent. That is a cost only, with no behavior difference.
- **WR-09** (committed codex evidence paths list is a lossy copy). Not hand-edited, by
  instruction. **The orchestrator regenerates the evidence sections of `20-SMOKE-CODEX.md` and
  `20-SMOKE-OPENCODE.md` from fresh harness output after these fixes.** The renderer changed
  (per-project paths, observed local install, compact line), so the old sections cannot be
  patched in place anyway.

## Owner review

- **WR-12: curated-config models do not reach compact agent variants.** On opencode, gsd-core
  1.17.0 installs 29 `gsd-<x>.compact.md` agent files with no `model:` line. The plan promises
  models only for the 35 `MODEL_PROFILES` agents. If GSD runs a compact variant on opencode,
  that agent uses opencode's default model, not the plan's. Both local smokes report this
  explicitly (`29 compact agent files carry no model: line; not compared`) and do not fail on
  it. Deciding whether this is a gsd-core gap to report upstream, or a known limit to document
  in SKILL.md, is the owner's call. (On codex the compact sources carry the same `name:` as the
  full agent, so the installer writes one TOML per name. This was read from the installer
  source and not checked further.)

## Superseded gate and verify strings

- **20-07 gate count:** "Matrix module ran 36" (20-07-SUMMARY.md:132; also
  20-SMOKE-CODEX.md:244 and 20-SMOKE-OPENCODE.md:359, "`Ran 36 tests`") is superseded. The
  loader now yields 27 tests (9 per host class, 3 classes), pinned by
  `TestMatrixModuleCollection`.
- **20-06 Task 2 `<automated>` verify** (the branch-consistency script) is superseded in two
  places. It fails by design on the new wording:
  - `root_pass = "verified by the Phase 20 opencode smoke" in followups.py` (and the matching
    host.py check) is now False, and `root_kept` is False too, so `assert root_pass !=
    root_kept` raises. Replacement pin: `test_phase_20_evidence_notes_claim_only_what_the_smoke_ran`
    in `tests/test_curated_config_followups.py`.
  - `inst_pass = "local layout and the --codex --local flags were verified" in followups.py` is
    now False, with `inst_kept` False, so `assert inst_pass != inst_kept` raises. Same
    replacement test.
  - Still true: `grep -c 'shipped npx launcher and its registry fetch were not exercised'
    followups.py` is 1, `grep -c 'Phase 20' followups.py` is at least 1, and `_gitignore_prefix_note`
    is present.
- `test_phase_20_evidence_notes_are_explicitly_verified` was renamed and rewritten as
  `test_phase_20_evidence_notes_claim_only_what_the_smoke_ran`.

## Verification

All gates ran in this worktree checkout (not an isolated review-fix worktree), with system
python3 and the checkout-local gsd-core 1.17.0.

- `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_followups tests.test_ai_kit_spec`: Ran 1015 tests, OK.
- `python3 tools/run_unittest_parallel.py --group unit`: 42/42 modules passed.
- `python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/snap.json`: `snapshot ok`.
- `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix`: `Ran 27 tests in 188.278s`, OK (loader count 27).
- `make validate`: exit 0. The first run failed on one pyright error in the new collection test; fixed in 21180be, then re-run green.
- **Local smoke, codex** (`--evidence-out tmp/p20/fix/local-codex.md`, artifacts in
  `tmp/p20/fix/local-codex-artifacts`): exit 0, 10/10 steps pass. Both projects show local
  scope, version 1.17.0 from inventory, and "35 agents; planned == baked == resolve-model".
  project-a's repeat install left the agents dir unchanged. The generated paths are identical
  in both projects (no extras). The protected set is unchanged. The matrix ran 420 checks.
- **Local smoke, opencode** (`tmp/p20/fix/local-opencode.md`, artifacts in
  `tmp/p20/fix/local-opencode-artifacts`): exit 0, 10/10 steps pass. The same chain holds for
  both projects, plus "29 compact agent files carry no model: line; not compared" per
  project. The generated paths are identical in both projects. The protected set is unchanged.
  The matrix ran 420 checks.
- Both smokes report `seed: absent`: no `~/.gsd/defaults.json` exists in this HOME today.

---

_Fixed: 2026-10-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
