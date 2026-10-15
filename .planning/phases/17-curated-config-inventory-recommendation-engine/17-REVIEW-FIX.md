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

## Pass 2

**Scope:** the Ponytail items PT-1..19 and the A/B/C Info items still open after pass 1, plus the misleading "isValidConfigKey unavailable" message noted above. Commits c4e1b27..1d475a1. No golden needed regenerating: an `UPDATE_GOLDEN=1` run left every golden byte-identical.

### Ponytail

- PT-1: already fixed in pass 1 (560026b rewrote `used_tiers` without the dead list).
- PT-2: 69bff9e. `_probe_gsd_tables` drops `host_name` and reuses the resolved node.
- PT-3: ed6502a. `detect_opencode_image_input` is removed and its tests are retargeted.
- PT-4, PT-5, PT-18, PT-19 (first half): e168985. Adds `_PI_NOTE`. `_codex_empty_slots` reuses `_slot_meta` and `_keep_why`. Layers that ignore prior entries take `_prior_entries`. `_slot_layer` calls `_host_cands`.
- PT-6: 1f2bd1d. One `gsd_catalog.SIBLING_MISSING`.
- PT-7: d462f59. `vendor.KNOWN_VENDORS` is derived from the prefix table.
- PT-8: already fixed in pass 1 (24918eb added the shared `_run`).
- PT-9: c4e1b27. The `plan_io` validator duplication is trimmed and every check is kept.
- PT-10: 39e7664. `clamp_effort` and `pick_variant` share `_nearest_effort`.
- PT-11: 83bdca9. `closed_key_set` starts from `MANAGED_KEYS`.
- PT-12: 193d038. `_score_axes = len(_entry_scores)`. The redundant seen set and router check are removed.
- PT-13: 6812bce. The refresh plumbing is flattened. `_RefreshJob`/`_CacheRead` are gone and max-locals is at 15/15.
- PT-14: 280d727. The inventory snapshot tuples are replaced by a dict of parts.
- PT-15: 46556b1. `gsd_tools` is loaded once in `resolve_gsd_core` and passed down.
- PT-16: 73e535b. `_item` takes its key from kind, and `_INERT_WHY` is a constant.
- PT-17: skipped. `claude_md_path_configured` is listed in plan 17-07, so it is kept as the pass-2 brief asked. Dropping it needs uz's confirmation.
- PT-19 (second half): already fixed in pass 1 (560026b restructured `_parse_tables_output`, so there is no re-check).

### Batch A Info

- A-IN-01: 2e6e12e. The unreachable scored branch of `choice_candidates` is removed.
- A-IN-02: 39e7664. An off-ladder target with no bare id picks the lowest step, independent of input order, with rule "lowest available".
- A-IN-03: 4f92b4f. An agent with no tier gets a specialist note on the execution, counterpart and vision paths.
- A-IN-04: e168985 and 83bdca9 (see PT-4 and PT-11).
- A-IN-05: partly fixed. e168985 removes the `del prior_entries` lines. The private NamedTuples stay, because inlining them breaks pylint max-args=5 and max-locals=15. The Ponytail review deliberately did not flag them.
- A-IN-06: 0414523. A keep that turns into an unset carries `value: null`.
- A-IN-07: cd6117c. An empty host list now reads "no <host> models enumerated".
- A-IN-08: d2852fa. The candidate sort moved into the public `plan_schema.inventory_digest`.
- A-IN-09: fixed in pass 1 (836c56f).
- A-IN-10: 39e7664. A lone `-max` (gpt-5.1-codex-max beside gpt-5.1-codex) is ranked as its own model. It counts as an effort step only when the family has another ladder-suffixed id. A shortcut comment marks the heuristic.
- A-IN-11: 0d868e0. A codex effort that the picked model does not list is marked "unverified" in `why`.
- A-IN-12: bda9bd2. The duplicate mock import and the unused `base` are removed.

### Batch B Info

- B-IN-01: c4e1b27 (see PT-9).
- B-IN-02: 69bff9e (see PT-2).
- B-IN-03: 44cdec9. A global `resolve_model_ids` omit gets the "read at resolution while .planning/ is absent" suffix.
- B-IN-04: 079f815. The warnings say "no cached runtimes snapshot" and "Artificial Analysis unavailable ...; catalog unscored" when there is no cache to fall back on.
- B-IN-05: b81ee36. The node calls (config-path and the tables query) use `deps.env_fn()`, and the gsd_run lookup uses `deps.which_fn`. The git calls still inherit the process env. Git does not read GSD_HOME, and threading env into the shared `gsd_tools.project_root` would change the v1 path.
- B-IN-06: skipped, because it needs a product decision. The review offers two options for the legacy `depth` key: surface it as an info item, or map it into `existing` for `granularity`. Both change plan output, and choosing between them is uz's call.
- B-IN-07: bda9bd2. The synthetic test roots come from `os.path.join(os.sep, ...)`.
- B-IN-08: the error prefix is fixed (0164049). Skipped: whether `--out` may create missing parent directories, and its 0600 mode. The review leaves both as decisions.
- Notes item: a757e2a. When node itself fails to start, times out or exits non-zero, inventory now reports "node failed to start / timed out / exited N: <stderr>" instead of "isValidConfigKey unavailable".

### Batch C Info

- C-IN-01: 1d475a1. `popen_fn`/`urlopen_fn` are threaded through `build_runtimes_snapshot` and `CliDeps`.
- C-IN-02: bf71d80. An unknown `image_input_source` is skipped instead of being relabelled. The test that pinned the relabel is updated.
- C-IN-03: ed6502a removes the wrapper. The snapshot docstring was fixed in pass 1.
- C-IN-04: ed6502a fixes the fixture handle and renames `OPENDCODE` to `OPENCODE`. The production urlopen and stdout handles were closed in pass 1.
- C-IN-05: the docstring is fixed (79c934d), together with the other stale docstrings in 826de40. Skipped: making the shared resolver pi-aware. That changes the v1 write path on pi hosts, which v1.3 keeps intact.
- C-IN-06: 2a01178. The skip message names the cause and the version found. Skipped: moving the class to the e2e tier. Other real-node classes also run in the unit tier, so it should be a tier-wide decision.
- C-IN-07: 2a01178. UPDATE_GOLDEN rewrites and then skips, so it never shows as a pass. The digest stays masked: the recommend tests pin the inventory -> digest link, and the masking is now documented.
- C-IN-08: bda9bd2 replaces the fragment list with a generic `ABSOLUTE_PATH` regex. The Artificial Analysis data part was fixed in pass 1.

### Verification (pass 2)

- Ran in the checkout `.claude/worktrees/v13-curated-config-v2`, with no extra isolated worktree, and with `PATH="$HOME/.local/bin:$PATH" UV_NO_SYNC=1 UV_OFFLINE=1`.
- `make test`: exit 0. 3382 Python tests passed (31/31 unit modules, 1/1 unit-uv, 4/4 integration, 2/2 e2e, 1/1 arch), plus 45/45 install.sh checks.
- `make validate`: exit 0 (ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest core and wizard).
- No live CLI probes and no network calls were made.
