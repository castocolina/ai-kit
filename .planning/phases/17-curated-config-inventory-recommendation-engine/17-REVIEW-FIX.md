---
phase: 17
fixed_at: 2026-10-15T00:00:00Z
review_path: .planning/phases/17-curated-config-inventory-recommendation-engine/17-REVIEW.md
iteration: 1
findings_in_scope: 30
fixed: 30
skipped: 0
status: all_fixed
---
# Phase 17: Code Review Fix Report

**Source review:** 17-REVIEW.md (batches A, B, C; Ponytail and other Info items deferred to a later pass)
**Scope:** every Critical and Warning in A/B/C, plus the three locked gray-area decisions (A-WR-04, A-IN-09, C-IN-08). Duplicates are merged: A-CR-01 == B-CR-01, A-WR-01 ~ B-WR-01. B-WR-10 shipped with CR-01.

## Fixed

| Finding | Commit | Fix |
|---|---|---|
| A-CR-01 / B-CR-01 | 560026b | `gsd_catalog` normalizes MODEL_PROFILES to profile-first at parse time. `roles` mirrors gsd-core's balanced fallback. `plan_io` makes an agent-first inventory exit 2. The golden-test transpose is deleted, and the fixture stays in raw node shape. |
| B-WR-10 | 560026b | The feeds-recommend test uses the agent-first shape and asserts plan content. TestRealGsdInventory runs real inventory then recommend for every host. |
| A-WR-01 / B-WR-01 | d89e62b | Every candidate and conflict field that recommend reads is validated. Non-UTF-8 inventories are rejected. An exit-2 backstop wraps build_plan. |
| A-WR-02 | 6bdeb1d | One duplicate-key set spans all layers. Conflicts are kept one per kind, and a project conflict wins over a global one. |
| A-WR-03 | d24813f | Codex keep (and empty-enumeration) entries show the native RUNTIME_PROFILE_MAP slot verbatim. 4 codex goldens regenerated. |
| A-WR-04 (locked) | e7731c2 | Claude specialists rank one row per alias, represented by its highest-version id. The `why` names that id, and an `effect` says the alias mapping is inferred. 3 claude goldens regenerated. |
| A-WR-05 | ac28928 | An unconfirmed review router points to Phase 18 cross-AI review selection, not to winning a slot. 4 opencode goldens regenerated. |
| A-WR-06 | 91ed64b | The vision note tells "image models unscored" apart from "no image model". |
| A-WR-07 | 8e3c2ee | A key in neither valid_keys list raises, so the CLI exits 2 with "rerun inventory". |
| A-WR-08 | 63af847 | Rejected keys are dropped per layer, so later layers only see entries that will be written. Rejected keys get no second leftover unset. |
| A-WR-09 | e1b9226 | An explicit cross-AI answer gets `source: user`. A defaulted one keeps `preset`. |
| A-WR-10 | 4271223 | A new pure `plan_schema` module holds PLAN_SCHEMA_VERSION, canonical_json and inventory_digest. `plan_io` is removed from the purity guard's allow-list. |
| A-IN-09 (locked) | 836c56f | review.*/effort.* are narrowed to default_reviewers, review.models., review.effort., effort.routing_tier_defaults. and effort.agent_overrides. D-08 is amended in 17-CONTEXT.md. |
| B-CR-02 | fac546e | write_plan resolves `--out` with abspath. Test: a bare `--out plan.json` from a temp cwd. |
| B-CR-03 | 8349827 | README/package.json are read with errors=replace, and ValueError is caught. The two listdir calls are guarded. |
| B-WR-02 | 9040ed0 | A nonexistent `--project-dir` exits 2. |
| B-WR-03 | f907ab4 | The shared `gsd_tools.config_path` uses timeout=10 and returns None on OSError or SubprocessError. |
| B-WR-04 | 4d7796d | A models.dev failure now warns even when AA succeeded. |
| B-WR-05 | 24918eb, 85fb6f6 | Refresh calls run in their own session. On timeout the group gets SIGTERM, then SIGKILL after 10 s. During the probe, SIGTERM unwinds through its cleanup. |
| B-WR-06 | bfa2bdd | The worktree warning is a single f-string, so a `{` in a path no longer crashes. |
| B-WR-07 | 4541c68 | The inventory help and module docstring say it runs the project's own gsd-core, so use it only on trusted checkouts. SKILL.md does not document inventory yet, so it is unchanged. |
| B-WR-08 | 864d55b | `vendor` is part of the spec-stack check. build_candidates raises, and inventory exits 2. |
| B-WR-09 | 667b566 | `--out` is refused when it points at the inventory, the project or global config, or anything under the config dir. |
| C-CR-01 | 24918eb | The probe sets OPENCODE_DISABLE_PROJECT_CONFIG=1 and runs from a private mkdtemp dir that is removed afterwards. |
| C-WR-01 | 24918eb | The loopback request goes through `ProxyHandler({})`. A test uses a real local server with http_proxy pointed at a dead port. |
| C-WR-02 | 24918eb, 6979bf5 | OPENCODE_SERVER_PASSWORD is dropped from the child env. A failed 2.x probe is recorded as `image_input_probe: failed` and shows up as an inventory warning. |
| C-WR-03 | 24918eb | The server runs in its own session, and the deadline timer and cleanup signal the whole process group. A blocked-pipe deadline test is included. |
| C-IN-08 (locked) | 973ad31 | Catalog scores and tokens_per_sec are now synthetic values that keep each axis's order. `_meta.fixture_note` marks them synthetic. 8 goldens regenerated, and the property tests still pass. |

All 30 in-scope ids (including the duplicates listed above) are fixed. None were skipped.

## Verification

- Ran in the checkout `.claude/worktrees/v13-curated-config-v2`, with no extra isolated worktree.
- `make test`: exit 0. 3371 Python tests passed across all tiers (31/31 unit modules, 1/1 unit-uv, 4/4 integration, 2/2 e2e, 1/1 arch), plus 45/45 install.sh checks.
- `make validate`: exit 0 (ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest core and wizard).
- Live run with a scratch HOME/XDG_CACHE_HOME, a copy of the checkout's gsd-core 1.16.0, and VOLTA_HOME pointing at the real volta toolchain: `inventory` then `recommend` exited 0 on claude, codex and opencode.
- A live run of the hardened probe, done before the coordinator's no-live-probe instruction, used a scratch HOME/TMPDIR. A planted MCP command did not run, planted disabled_providers were ignored, and http_proxy was bypassed. Only private probe servers were started; uz's `opencode serve --service` was never signalled.

## Notes

- `TABLES` in test_curated_config_recommend.py stays profile-first. That is now the inventory contract.
- Under a scratch HOME the volta node shim fails, and inventory reports it as "isValidConfigKey unavailable". This message predates these fixes and is misleading; it belongs to the Info pass.
