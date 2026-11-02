# Phase 23: Host-split status line for Claude Code and Cursor CLI - Research

**Researched:** 2026-10-23
**Domain:** stdlib-only Python status-line renderer split, Cursor CLI `statusLine` contract, private Dashboard quota client, multi-host installer/wizard
**Confidence:** HIGH for the Claude-side split and the Cursor runner contract (read from code this session); MEDIUM for Dashboard behavior (bundle logic plus one POC run, no raw responses on disk); LOW for anything needing a live session (cadence, latencies, token lifetime).

Provenance: `[VERIFIED: path:lines]` = file opened with Read/sed this session; `[VERIFIED: ast]` = recomputed with `ast`; `[VERIFIED: bundle]` = read from the installed `cursor-agent` bundle `versions/2026.10.14-941492e` (public JS, no config/auth file touched); `[CITED: ...]` = a repo document; `[ASSUMED]` = inference, needs owner confirmation.

<user_constraints>
## User Constraints (from 23-CONTEXT.md)

### Locked Decisions
D-01..D-24 in `23-CONTEXT.md` are locked and NOT reopened here (audit table = 182 rows; role-module layout; neutral `Context` + typed `ctx.host`; arch rules + anchored `rg -P` reference check; oracle first then pure move; shared nullable `context` segment; pure `util_window_gap` + Claude adapter; four Cursor segments, API off by default; per-segment windows; `/usage`-logic normalization; derive-else-hide; POC reference only; cache-only render + single-flight detached refresher as the working presumption; scratch `CURSOR_CONFIG_DIR` capture; https-only/`*.cursor.sh`/refuse-all-redirects transport + `auth.json` path mirroring the CLI; cache/state function; post-split robustness fixes; per-host provider namespace; one create-if-absent helper; host-derived config env; separate `Paths.cursor_config_dir`; host-keyed wizard seam; per-host detect/wire/unwire; real-entry wizard preview on a synthetic cache). Where a premise drifted, section 1 says so; the decision stands unless an Open Question says otherwise.

### Claude's Discretion
- File names of the audit table and scripts; the exact `HostView` field names; refresher lock margin; the stale-marker glyph.

### Deferred Ideas (OUT OF SCOPE)
- The Cursor hooks path mismatch: backlog 999.2.
- An auto-only Cursor segment and the design's scalar toggles (D-08).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STL-01 | Split into `common_*`/`claude_*` + thin entry, byte-identical Claude render, hard-rename migration | Sec. 1 (counts verified, test blast radius), Sec. 2 plans 01-07, Sec. 5 oracle gaps |
| STL-02 | Cursor line, three quota segments + reset, shared gauge, providers unchanged | Sec. 4 (payload), D-07/D-08/D-09 mapping in Sec. 2 plans 06/12/13 |
| STL-03 | `cursor_quota.py` only network/credential code; normalization; cache/failure | Sec. 3 (buildable on fakes), Sec. 4.3 (auth.json facts), Sec. 5 |
| STL-04 | Spike before choosing inline vs refresher | Sec. 3 (owner-only runbook + checker), Sec. 4.2 (runner semantics already verified) |
| STL-05 | Multi-host setup, doctor `--host`, two-host wizard | Sec. 1.4 (seam drift), Sec. 2 plans 14-15 |
</phase_requirements>

## Project Constraints (from AGENTS.md)
- Runtime code stays stdlib-only; heavy deps only through guard + re-exec + fail-closed. All runtime writes to host configs atomic (`mkstemp` + `os.replace`), reusing `_read_json_checked`/`_atomic_write_json`.
- Never present a result with more certainty than its sourcing (inferred quota is `≈`; reverse-engineered formats flagged).
- `skill-judge` loop applies only to `SKILL.md` changes (none expected here).
- One coherent buildable commit per logical change with tests + docs; no `--no-verify`; fold related commits before closing a plan.
- Never hardcode an absolute path in source/tests/assets; no real configs as fixtures; scratch under `./tmp/`.
- `make test` (unit, integration, e2e, arch) and `make validate` must be green; `tests/test_arch.py` extended, never bypassed, and each rule needs a `TestArchNonVacuity` twin; a new `tests/test_*.py` joins the `unit` group automatically but the generated listing in `Makefile`/`.pre-commit-config.yaml` must be refreshed with `tools/gen_test_groups.py` (`tests/test_gate_scope.py` fails while stale) [VERIFIED: tools/gen_test_groups.py:1-8].
- Parallelism never hardcoded (<= 40% of CPUs); wizard changes need a real `uv run` of `tools/wizard_app.py`; kill spawned processes.
- Plans must be cross-AI reviewable, cheap-model executable, path-agnostic. Update README/nested docs in the same change.

## Summary

The split is mostly mechanical and the current tree is a good starting point: `tools/status-line.py` is byte-identical in structure to what CONTEXT audited (last touched 2026-10-13, `c22b9de`), so every `tools/status-line.py` line citation in CONTEXT still holds and the 134 + 7 + 41 = 182 audit count reproduces exactly. What drifted is everything around it: `tools/setup.py` grew from ~3560 to 3930 lines through Phases 21-22 (every `setup.py:NNN` citation is stale by ~370 lines), the wizard gained fields, the Makefile/pre-commit now carry a generated test-group listing, the D-04 reference list is partly obsolete (and incomplete: 159 hits in 28 files outside the history allowlist), and the installed `cursor-agent` is 2026.10.14 rather than the audited 2026.10.01 (the statusLine contract and payload builder are unchanged between them).

The existing golden test is NOT a byte-identity oracle: it strips ANSI, renders 4 payloads with default segments (alt segments off, no `effort`/`todo`/`lines`), and disables `render_time`/`slowest`. D-05's first commit therefore has real work to do. Separately, a "pure move" cannot also neutralize `Context` (`ctx.host`) in one step; plan the neutralization as its own oracle-gated commit.

The Cursor side is better evidenced than CONTEXT assumed: the runner semantics (argv spawn, SIGTERM-on-abort, debounce with `maxWait`, output rules, timeouts) and the payload builder were read from the installed bundle, and a real payload plus a 1.9 s cold sequential fetch already exist in the POC worktree. Only live-session facts (cadence, p50/p95, real raw Dashboard responses, token lifetime, real `param_summary`) are owner-only. Everything else in the spike can be turned into a runbook + redaction/plausibility checker, a runner simulator and a loopback Connect-JSON fake server, so Part B can be built and tested without a Cursor login.

**Primary recommendation:** plan in two slices. Slice 1 (now): oracle + audit + staged pure move + Context/HOST neutralization + gauge + migration + setup/doctor per-host wiring + the spike tooling (so the owner can run the runbook while Part A executes). Slice 2 (after the owner's spike record lands, honoring AGENTS.md "spike before plan"): `cursor_quota`, Cursor host/segments/providers, wizard seam, close-out. Keep D-13 (cache-only + detached refresher) as the presumption; the POC's 1.9 s cold fetch against a 300 ms debounce already makes an inline fetch implausible.

## Architectural Responsibility Map

This is a local CLI toolchain, not a web stack; tiers are mapped to process roles.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Payload parse to neutral Context | Host adapter (`claude_payload`/`cursor_payload`) | `common_render` | Payload shape is host data; Context is the neutral contract (D-03) |
| Layout/pack/render | `common_render` | host `HOST` object | Never names a host; receives `HOST` as an argument |
| Gauge color/sign | `common_fmt`/util leaf | host segments | Pure function of (pct, start, end, now) (D-07) |
| Network + token | `cursor_quota` only | detached refresher process | One module owns transport/credential; render reads cache only (D-13/D-15) |
| Quota cache + lock | `cursor_quota` (files under cache base) | refresher | Single-flight across processes, atomic 0600 writes (D-16) |
| Host config wiring | `setup.py` (per-host detect/wire/unwire) | `*_host` modules (lazy import) | Atomic JSON primitives shared (D-23) |
| Wizard flow | `wizard_app` (host-keyed, imports nothing host-specific) | `setup.py` builds `HostView`s | Seam rule from D-22 |
| Doctor `--host` | `statusline-doctor.py` | `*_host`, `cursor_quota` foreground diagnostic | Diagnostics stay out of the render module (arch rule 7) |

## 1. Drift Report: CONTEXT premises vs HEAD (93fa9db, 2026-10-23)

### 1.1 D-01 audit counts - confirmed [VERIFIED: ast]
`ast.parse(tools/status-line.py).body`: 134 `FunctionDef`, 7 `ClassDef`, 41 `Assign` (every target is a single `Name`; no tuple targets, no `AnnAssign`/`AugAssign`) = 182 rows; def+class subtotal 141. Non-row top level: 9 `Import`, 4 `ImportFrom`, 1 `Try`, 1 `If`, 1 docstring `Expr` (these must be handled by the splitter as module preamble, not audit rows). Per banner block (9 banners at lines 65, 283, 693, 1180, 1276, 1739, 2284, 2519, 2555): DEFAULTS 23 assigns + 5 classes; cfg 21 defs; probe 27 defs + 1 assign; fmt 7 defs + 2 assigns; util 30 defs + 12 assigns; core 26 defs + 2 classes + 1 assign (`BUILDERS`, line 2499); seg 21 defs + 1 assign; SHELL 2 defs (`main`, `safe_render`). 21 `seg_*` functions. `git log` for the file: last change `c22b9de` 2026-10-13, before CONTEXT (2026-10-14) -> no code drift.

### 1.2 Line citations into `tools/status-line.py` - all still correct [VERIFIED: sed/ast]
`SEGMENTS`:72, `RIGHT_MARGIN`:96, `LAYOUT`:113, `PINNED`:123, `_RAMP_DEFAULTS`:168, `_EFFORT_DEFAULTS`:189, `min_rows` read:503, `cfg_load_config_verbose`:565-650 (calls `core_discover_external` at 615), `cfg_load_config`:653, `probe_git_worktree_info`:760, `probe_git_snapshot`:831, `util_rate_gap`:1493, `util_gap_sign`:1527-1533, `util_rate_group_str`:1677, `context_pct`/`context_max` `or 0` coalescing:1826-1827, `core_doctor_cmd`:1833, `core_discover_builders`:1943 (`globals()` at 1952), `core_run_provider`:2056-2078, `core_safe_build`:2131, `BUILDERS`:2499, `safe_render`:2522, `main`:2540. Quoted: `BUILDERS = core_discover_builders()   # module-level snapshot; same shape as the old literal`. `HOST` does not exist yet (`rg "HOST\b" tools/*.py` empty): D-03's "`HOST` gains ..." means "the new `HOST` type has ...".

### 1.3 D-01 taint numbers - NOT reproducible
CONTEXT states "29 direct seeds, 9 by propagation" but never records the seed vocabulary. A reproduction with the vocabulary `claude|CC_AI_KIT|rate_limits|settings.json|.claude` (case-insensitive, over each def/class source) gives 23 seeds + 10 propagated = 33 (not 38). **Action:** the audit script must pin its seed vocabulary in code and the table must record per-row `taint_reason`; do not copy the 29/9 figures into acceptance checks. Rows to hand-classify regardless (data-source taint a token grep misses): `probe_transcript_bytes`:955, `util_iter_tool_uses`:1558, `util_pick_from_tasks`:1576; over-flagged: `cfg_load_config*` (only the `CC_AI_KIT_` literals; fate "generalized").

### 1.4 Other files - drift table

| CONTEXT premise | HEAD reality | Impact |
|---|---|---|
| `setup.py` citations (`:51-110`, `:232-283`, `:455-513`, `:1760-1773`, `:2237-2240`, `:2413-2560`, `:2913-2927`, ...) | File is 3930 lines; all shifted ~+370. Current anchors: `resolve_paths`:56, `SEGMENT_DEFAULTS/LAYOUT_DEFAULTS`:94-118, `render_preview`:242, `write_toml_preserving`:463, `discover_external_segments`:744, `_read_json_checked`:1620, `_atomic_write_json`:1641, `_statusline_command`:1881, `wire_statusline`:1925, `detect_statusline`:1984, `copy_recipe_if_absent`:2016, `unwire_statusline`:2032, `save_statusline_config`:2238, `_recover_incompatible_config`:2584, `persist_statusline`:2621, `_sample_input_path`:2663, `_build_wizard_context`:~2794, `_headless_wire_statusline`:3371, `cmd_uninstall`:3621, `--with-statusline` argparse:3848 | Plans must cite symbols, not lines. |
| `Paths` | namedtuple at :48-54 has `cursor_dir`, `cursor_hooks`, `opencode_dir` (Phase 21/22 additions) but no `cursor_config_dir`; `cursor_dir = CURSOR_CONFIG_DIR or ~/.cursor` (:69) | D-21 confirmed: add a separate field, leave `cursor_dir` (hooks). |
| D-19 "create-if-absent used by `_recover_incompatible_config`" | That function (:2584-2618) backs up to `<file>.bak` then `shutil.copyfile(paths.sample, cfg)` over the incompatible file - an overwrite, not create-if-absent | The helper does not fit; use an atomic replace (mkstemp + `os.replace`) there and keep the helper for `copy_recipe_if_absent` (:2016, currently `isfile` check then `open(..., "w")`, racy) and the TOML migration. |
| Wizard `:598-640` Claude strings | `tools/wizard_app.py` is 1085 lines; hard-coded Claude text now at ~:703-705 ("Write ~/.config/ai-kit/statusline.toml + wire settings.json"), ~:736-741 ("Open a new Claude Code session ..."); `WizardContext` at :119 has more fields than CONTEXT knew (`component_meta`, `housekeeping`, `segment_meta`, `external_segments`, `status_line: StatusLineFn`) | D-22 still right; `HostView` replaces the single `status_line`/`segment_meta`/`external_segments`/`sample_json`/`engine` group. |
| `WizardContext` single test construction site (`tests/wizard_fixtures.py:34`) | Two sites: `tests/wizard_fixtures.py:36` and production `tools/setup.py` `_build_wizard_context` (:~2794) | Both change in plan 15. |
| D-04 reference list: `Makefile:70`, `pyproject.toml:88,94`, `.pre-commit-config.yaml:27,50,56`, `AGENTS.md:29,90` | Makefile/pre-commit now only contain the generated `tests.test_*` listing (no `status-line.py` path); `pyproject.toml` only line 1 comment; AGENTS.md hits are lines 29 and 86 | Re-run the anchored check; do not trust the old list. |
| Reference blast radius "README (11)" etc. | `rg -P '(?<![\w-])(status-line\.py\|statusline\.toml)'` outside `.planning/**`, `docs/superpowers/**`, `docs/prds/**`, `.claude/**` = 159 hits in 28 files: `tests/test_setup.py` 46, `tools/setup.py` 23, `docs/refactor/lint-ruleset-and-triage.md` 12, `README.md` 11, `tests/test_wizard_pty.py` 6, `tests/test_status_line.py` 6, `tests/test_external_segments.py` 6, sample TOML 5, `tools/status-line.py` 5, `tools/statusline-doctor.py` 5, `tests/test_arch.py` 5, `tests/test_system_memory_e2e.py` 4, `docs/wizard-redesign/**` 6, `tests/test_worktree_e2e.py` 3, `wizard_app.py` 2, `test_tool_substitution_hook.py` 2, `skills/ai-kit-project-rules-arch/.../ast_only.py` 2 (a docstring example), `AGENTS.md` 2, plus single hits in `tools/install.sh`, `tests/test_install.sh`, `tools/hooks/precompact_core.py` (docstring/comment), `skills/ai-kit-spec-review/.../config_io.py` (comment), `tests/test_statusline_doctor.py`, `tests/test_claude_precompact.py`, `pyproject.toml`, `docs/architecture/status-line-pipeline.md` | Open Question 3: extend the history allowlist to `docs/refactor/**` and `docs/wizard-redesign/**`, or edit them. Comments in `precompact_core.py`/`config_io.py` are real references and must be edited. |
| `tests/test_arch.py` citations `:46,133,197,377-381,590-640` | File is 925 lines. Anchors now: `_BLOCK_PREFIX`/`_SHELL_ENTRYPOINTS`:~53-65, `_defined_names`:136, `check_config_env_in_cfg`:200, `_BROAD_EXCEPT_BACKSTOPS`:~385-394 (keys on the string `tools/status-line.py`: `core_safe_build`, `safe_render`), `check_role_prefix_integrity`:319, rules at :512-640, `TestSegmentInventory`:874 (loads `tools/status-line.py` by path via `_sl()` and reads `sl.SEGMENTS`/`sl.LAYOUT`) | The broad-except allowlist, rule 6 block map, rule 1 (`_CONFIG_ENV_PREFIX = "CC_AI_KIT_"`), `TestSegmentInventory` and the module-level `setup` loader (:40-43) all break at the rename and are part of the move plan, not follow-ups. |
| D-05 "only loaders, fixture helpers and `mock.patch.object` targets may differ" | `tests/test_status_line.py` (2889 lines, 99 distinct `sl.X` names, 561 `sl.` refs, 78 `mock.patch` uses) also has 6 `patch.dict(sl.BUILDERS, ...)` uses and `patch.object(sl, "core_build_context")`. `BUILDERS` disappears with D-02's discovery | Extend the allowed-difference set to "registry handle" (`BUILDERS` -> the new registry object) and state it in the conformance script. `patch.object(sl.subprocess/sl.time/sl.os, ...)` patch the shared stdlib module and survive any split. |
| D-18/D-20 env naming | Provider env mirror today is `AI_KIT_SEGMENT_{COLS,ID,LINE,POSITION}`, toggles are `CC_AI_KIT_SEGMENT_<KEY>` [VERIFIED: tools/status-line.py:2056-2078 and :350-380]. D-18 puts the Cursor provider env at `AI_KIT_CURSOR_SEGMENT_*` while D-20 puts Cursor toggles at `AI_KIT_CURSOR_SEGMENT_<KEY>` | Same prefix for two meanings: a segment id `cols`/`id`/`line`/`position` would collide. Open Question 1. |
| Cursor bundle 2026.10.01 | Installed `versions/` has 2026.09.15, 2026.10.01, 2026.10.14 (latest). Payload builder and runner identical in 10.01 and 10.14 (checked by string probes); 09.15 lacks the interval handling | Facts below are re-verified on 10.14. |
| `render` latency "41.5 ms p50 / urllib 18 ms" | Re-measured: render p50 39.9 ms, p95 50.9 ms (30 runs, sample-input, `-S`); `import urllib.request` adds ~19.6 ms over an empty interpreter (24.3 vs 4.7 ms) [VERIFIED: local run] | D-04's lazy-import rule is still justified. |
| `setup.py` "Duplicated here, not imported" defaults (comment at :92-95) vs design 6.2 "delete the duplication, import `common_config`" vs D-03 "setup imports host modules lazily" | Not reconciled in CONTEXT | Open Question 2. |

Baseline: `python3 -m unittest tests.test_status_line tests.test_arch tests.test_statusline_doctor` passes at HEAD in ~2.3 s [VERIFIED: local run]. Sibling imports under `python3 -S`, including through a symlinked entry, resolve (`sys.path[0]` is the script's real directory) [VERIFIED: local run, Python 3.14.7], so thin entries need no `sys.path` hack beyond what `tools/hooks/` already does.

## 2. Recommended Plan Decomposition

Sizing rule used: <= 3 tasks per plan, each task one commit-sized change a cheap model can finish in a 3600 s budget, with an executable acceptance command. "Oracle" = the D-05 golden/entry/provider captures; every Part A plan from 02 on must keep it green. Plans touching the same file are serialized (parallel edits to `tests/test_arch.py` or `tools/setup.py` conflict); different-file plans share a wave.

### Slice 1 (plan now)

**Wave 1 (independent, parallel)**
- **23-01 Oracle + audit generator.** T1: ANSI-preserving golden for payload variants that turn every segment on (extend `tests/fixtures/golden/inputs.json` or add `inputs_full.json`: `rate_limits` with `five_hour`+`seven_day`, `cost`, `effort`, `todo` transcript fixture, `lines`, plus the 4 existing widths; config enabling the `alt_*` segments; keep `render_time`/`slowest` off - they are time-dependent) compared byte-for-byte including escapes; T2: entry-level subprocess render (`python3 -S tools/status-line.py` with a fixed env, `TZ`, `HOME`, `XDG_*`, `STATUSLINE_COLS/LINES`) and a strict-provider capture (a provider script that records stdin bytes, the sorted env key set it sees, and the cache path used) stored as a fixture for R10; T3: `ast`-based audit generator emitting the 182-row machine-readable table (name, kind, target module, neutral y/n, reason, fate), the count check against the base blob (`git show <base>:tools/status-line.py`), and the taint cross-check with a pinned seed vocabulary. Acceptance: `python3 -m unittest tests.test_status_line_golden tests.test_statusline_audit`.
- **23-02 Spike tooling (Slice-2 prerequisite; runs in parallel with Part A).** See section 3. T1: redaction + plausibility checker and fixture schema; T2: loopback Connect-JSON fake Dashboard server + runner simulator; T3: owner runbook (`tmp/` scripts that the owner runs, outputs only to `./tmp/spike/`). Depends on nothing in Part A.

**Wave 2**
- **23-03 Reviewed audit rows.** The 182 rows need a human/Opus-reviewed `reason` and `fate`; defaults come from the generator (block role -> module), so the executor only edits the ~40-60 non-default rows (taint mismatches, mixed `_RAMP_DEFAULTS`, `SEGMENTS`/`LAYOUT`/`PINNED`, `Context`, `Config`). Output is the committed table and the rewrite map used by 04-06. Keep this a separate plan so a cheap executor does not conflate judgment with mechanics; cross-AI review of the table is the quality gate.

**Wave 3: staged pure move (each stage buildable; `sl.X` -> `<module>.X` rewrite of tests done by a script driven by the audit map)**
- **23-04 Leaf stage:** types/defaults leaf, `common_fmt`, neutral `util_`, Claude-only `util_` (rate window, tool-use/task pickers). T1 mover script + per-definition `ast.dump` equality conformance test (moved body == base blob body); T2 apply to blocks 1, 4, 5; T3 rewrite test qualifiers, keep oracle green.
- **23-05 Config/probe stage:** `common_config` (cfg_ with primitives instead of `HOST`; external-discovery relocation per D-02), `common_probe`, `claude_probes`. Patch targets: tests patching `probe_*` must patch the module the *caller* looks them up in. To make that stable, callers use module-attribute access (`import common_probe as probe`; `probe.probe_git_snapshot(...)`) so a single patch on the defining module works - state this in the conformance script as the one allowed call-site rewrite.
- **23-06 Render/segment/shell stage + rename:** `common_render` (Context, Theme, packer, `main`/`safe_render`), `common_segments`, `claude_segments`, `claude_payload`, `claude_host`, thin `tools/claude-status-line.py`, `git mv` of the sample TOML, doctor loader, `tests/test_arch.py` rule-6 per-module prefix map + rule-9 allowlist keys + `TestSegmentInventory` loader + dependency-direction rules (each with non-vacuity twin), `docs/architecture/status-line-pipeline.md` deleted. This is the largest plan; split into 06a (move + entry + doctor + tests green) and 06b (arch rules + non-vacuity + inventory `line` per host) if the executor budget is tight. It is the only plan allowed to leave `status-line.py` deleted.
- **23-07 Reference sweep:** update the ~159 references (section 1.4), README(s), AGENTS.md architecture bullets (line ~86), `skills/.../ast_only.py` docstring, hook comments; add the anchored `rg -P` check as a test with the history allowlist (decide Open Question 3 first).

**Wave 4 (behavior changes, each its own commit, oracle must stay green except where stated)**
- **23-08 Context neutralization + HOST + registry (D-02/D-03):** Production use of the Claude-only `Context` fields is tiny (`ctx.effort`, `ctx.added`, `ctx.removed`, `ctx.cost`, `ctx.total_ms`, `ctx.api_ms`, `ctx.session`, `ctx.claude_dir` 1 use each, `ctx.transcript` 4, `ctx.rate_limits` 2 [VERIFIED: grep]) and `Context(` is built in 2 test sites, so this is a small mechanical commit once the move is done. The duplicate-id startup error replaces the `globals()` registry; `patch.dict(sl.BUILDERS)` tests move to the registry object (section 1.4).
- **23-09 Gauge generalization (D-07) + robustness (D-17):** `util_window_gap` + Claude adapter (keep `util_gap_color`/`util_gap_sign` unchanged; boundaries 5/11/15/15.01 tests); git `timeout` + `TimeoutExpired` with a fake slow `git` on `PATH`; `cfg_load_config` inside `safe_render`'s try (the `min_rows = "x"` crash at line 503 is real on Claude today). A behavior change by design: it adds error-segment output for a bad TOML, so it is the one place golden expectations may gain a new fixture, never an edited one.
- **23-10 Migration + create-if-absent (R3, D-19):** setup rewrites a Claude `statusLine.command` that points at ai-kit's old `status-line.py` (anchored match on the install-dir path, so `claude-status-line.py` and foreign commands are untouched), moves `statusline.toml` -> `claude-statusline.toml` (link + unlink; both present -> warn, change nothing), `copy_recipe_if_absent` on the shared helper, 16-process race test. `Paths.status_line`/`config_toml`/`sample` rename lands here. Ordering per SPEC: rewrite command first, then TOML move.

**Wave 5 (setup side of Part C; needs only the entry file names, not the Cursor renderer)**
- **23-11 `Paths.cursor_config_dir`/`cursor_cli_config`, per-host detect/wire/unwire, headless `--with-statusline[=claude,cursor]` (`nargs="?"`), per-host `cmd_uninstall`, doctor `--host`.** Reuse `_read_json_checked`/`_atomic_write_json`; Cursor shape check is `type == "command"` plus non-empty string `command` [VERIFIED: bundle zod schema `a=s.Ik({type:s.eu("command"),command:s.Yj().min(1),padding:s.ai().int().min(0).optional(),updateIntervalMs:s.ai().int().positive().optional(),timeoutMs:s.ai().int().positive().optional()})`]. Mirror `wire_hook_cursor`'s "do not materialize when the parent dir does not exist" rule (:1846-1856) for detection. Detect/wire matrix 3 states x 2 hosts x interactive/headless.

### Slice 2 (plan after the owner's spike record, per AGENTS.md "spike before plan")
- **23-12 `cursor_quota` pure core:** `QuotaResult`, normalization (D-10/D-11), state function (D-16) - tests on bundle-derived synthetic fixtures plus the owner's redacted real responses (section 3).
- **23-13 `cursor_quota` transport + credentials:** `validate_endpoint`, refuse-all-redirects opener, `auth.json` reader mirroring `getAuthFilePath`, concurrent three-call fetch with per-call timeouts, loopback fake-server tests, lazy-import arch rule + non-vacuity.
- **23-14 Cache/lock/refresher:** single-flight `O_EXCL` lock with pid + start time and expiry, negative cache, detached `--refresh` entry (`python3 -S ... --refresh`, `start_new_session=True`, `close_fds=True`, stdio DEVNULL), killed-refresher and concurrent-render tests using the runner simulator.
- **23-15 Cursor payload/host/segments/entry:** `cursor_payload`, `cursor_segments` (four segments, `≈`, stale marker, per-segment window via D-09), `cursor_host`, `cursor-status-line.py`, `cursor-statusline.toml.sample`, inventory `line`, synthetic payload tests including null/absent fields, each on-demand state, `render_width_chars` precedence.
- **23-16 Providers + host-derived env (D-18/D-20):** Cursor provider namespace and `AI_KIT_CURSOR_*` config env, strict-provider capture compared post-split, "Claude never scans the Cursor dir".
- **23-17 Wizard host-keyed seam + preview (D-22/D-24):** `HostView`, two-host flow, `synthetic_cache()`, wizard fixtures, two-host PTY test (extend `tests/test_wizard_pty.py` patterns).
- **23-18 Close-out:** READMEs, `tools/gen_test_groups.py` refresh, `make test` + `make validate`, `/gsd-secure-phase`, owner-recorded live runs (section 3), process cleanup.

Parallelism note: 23-02 and 23-01 can run together; 23-12/13 can run in parallel with each other (disjoint files, but both add arch rules - give 13 the arch edit and have 12 add only its own test module). Never run two plans that edit `tests/test_arch.py` or `tools/setup.py` in the same wave.

## 3. R5/D-14 Spike: owner-only versus buildable

**Owner-only (cannot be done on synthetic data; none of it is performed by this research):**
1. A real `cursor-agent` TUI session (login, quota use, token read through `auth.json`) under a scratch `CURSOR_CONFIG_DIR` (D-14) - the only source of: the real payload on a parameterized model (`param_summary`, `max_mode`), real update cadence during streaming (shortest/typical gap), the real kill-by-next-update behavior, real `render_width_chars` vs the terminal.
2. Real Dashboard calls with the owner's token: raw responses (units, optional-field presence on the owner's plan, `included_usage_period`, `on_demand_spend_disabled_by_organization`, on-demand classification), p50/p95 latency for sequential and concurrent calls.
3. Token facts: lifetime, whether the CLI rewrites `auth.json` while a reader reads (the write is non-atomic, see 4.3), observed 401 behavior (or "unknown").
4. Final R12 live run with the wired line, and approval for anything that touches `~/.cursor` (D-14's fallback path only).

**Buildable and testable without the owner (do these in 23-02):**
- **Bundle-derived payload contract.** The payload fields, types and conditionality are fully specified by the bundle builder (4.1). Commit a typed synthetic payload plus a test that fails when a field disappears; the POC's real payload (redacted keys below) is a second fixture. This already satisfies "payload shape (redacted)" for everything except the live `param_summary` value.
- **Runner simulator** (test helper, stdlib): spawn `argv` with `shell=False`, write the JSON payload to stdin, close stdin, optional SIGTERM after N ms to the direct child only, stdout post-processing identical to the CLI (4.2). Lets 23-14 prove "refresher survives the kill, cache written, next render served" and "killed render holding the lock does not wedge the next one" deterministically.
- **Loopback fake Dashboard** (Connect-JSON over HTTP on 127.0.0.1, scripted per method): cents ints, dollar `hardLimit`, `>= 2147483647`, epoch ms as numbers and strings, missing optionals, 401/403, slow response, 301/302 to a foreign origin (to prove the bearer is not forwarded), malformed JSON. Transport tests inject the opener below the endpoint validator; the validator itself is a pure function tested with `api2.cursor.sh` (pass), `cursor.sh.evil.com`, `http://api2.cursor.sh`, userinfo, port != 443 (fail). Never weaken the production validator for tests.
- **Checker (`spike_check`)**: validates the owner's output bundle in `./tmp/spike/` before anything is promoted to `tests/fixtures/`: schema; a redaction scan (no `eyJ`-style JWTs, no `Bearer`, no `@`, no UUID/session ids, no token-length hex/base64 runs); plausibility invariants (`*_percent_used` within 0-100 or absent, spend ints, `hard_limit` numeric, epoch ms in a sane range, `billing_cycle_end > start`); computes p50/p95 from the raw samples; and applies a pre-declared decision rule so the owner does not judge: inline fetch only if concurrent p95 + render p95 < the shortest observed update gap AND < the 300 ms debounce floor, otherwise detached refresher (D-13). The POC's measured cold sequential fetch was 1921 ms [VERIFIED: POC `tmp/cursor-statusline-poc-FINDINGS.md`, "cold_fetch_wall_ms: 1921"], so the rule is expected to confirm D-13.
- **Owner runbook** (`tmp/spike/README` + scripts): scratch config dir creation (`cli-config.json` copy plus `statusLine` -> a capture script; never writes the real file), a throwaway Dashboard probe that reads `auth.json` read-only, writes only redacted JSON and timings to `./tmp/spike/`, refuses non-`*.cursor.sh` endpoints using the same validator rules, and prints a one-screen summary the owner pastes into the spike record. Use the existing POC capture only as a reference; it reads the real `cli-config.json` and leaves `tmp/cli-config.json.bak` (0644, contains `authInfo`) which D-12 requires deleting.
- **Spike record** `23-SPIKE.md` (amend SPEC R5 "the phase RESEARCH records ..." to point here) carries machine-checked front matter that Slice-2 plans gate on with a `checkpoint:human-verify` task.

Redacted shape of the POC's real captured payload (types only) [VERIFIED: POC `tmp/cursor-payload.json`, values replaced by types; only numerics kept]: `session_id`, `transcript_path`, `render_width_chars` (153), `cwd`, `autorun` (bool), `model{id, display_name}`, `workspace{current_dir, project_dir, added_dirs[]}`, `version`, `output_style{name}`, `context_window{total_input_tokens 226304, total_output_tokens 62517, context_window_size 256000, used_percentage 88.4, remaining_percentage 11.6, current_usage{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}}`, `session_name`. No `param_summary`/`max_mode` on that account. The POC's real quota render showed `inc 47% auto 41% api 100% reset 2026-11-10 od $5.2/$5` (rendered values only; **no raw Dashboard responses were saved**, so the "redacted real responses" in SPEC R7 do not exist yet).

## 4. Cursor CLI status-line contract as installed (2026.10.14-941492e)

### 4.1 Payload (built per render, `7000.index.js`) [VERIFIED: bundle]
Top level: `session_id`, `transcript_path`, `render_width_chars`, `cwd`, `autorun`, `model{id, display_name, param_summary?, max_mode?}`, `workspace{current_dir, project_dir, added_dirs: []}`, `version`, `output_style{name: "compact"|"default"}`, `context_window{total_input_tokens, total_output_tokens, context_window_size, used_percentage, remaining_percentage, current_usage}`; optional `session_name`, `vim{mode}`, `worktree{name, path}`. Quoted builder fragments: `n=Math.max(0,(process.stdout.columns??80)-4)` (so `render_width_chars = columns - 4`, 76 when the TTY width is unknown); `...o?{param_summary:o}:{},...Wn&&!0===f?.maxMode?{max_mode:!0}:{}`; `context_window_size:ne??null,used_percentage:le??null` and `remaining_percentage` = `null` when `used_percentage` is null (so the context fields are null before the first token count). `param_summary` is only set when `modelManager.hasParameterizedModels()` and a parameterized model is selected. No `cost`, no `rate_limits`, no `effort` field. **Inferred:** whether `param_summary` actually carries reasoning effort for the owner's models (live value unobserved).

### 4.2 Runner: spawn, debounce, abort, output [VERIFIED: bundle `./src/hooks/use-status-line.ts` and `use-debounced-callback.ts`]
- Config object `{type:"command", command, padding?, updateIntervalMs?, timeoutMs?}`; interval = `max(300, updateIntervalMs ?? 300)`; timeout = `max(50, timeoutMs ?? 2000)`; `padding ?? 0`.
- Command is split with `string-argv` (`(0,c.A)(e)`), first token `~`/`~/` expanded, then `spawn(file, args, {cwd, env: process.env, shell: false, stdio: ["pipe","pipe","pipe"]})`; JSON payload written to stdin then stdin ended; `cwd` is the workspace dir (`bn`). Env is the CLI's full `process.env` (so `CURSOR_*`, `XDG_*`, `CURSOR_API_ENDPOINT` reach the command).
- Debounce: `useDebouncedCallback(..., b, {maxWait: b, leading: true, trailing: true})` - fires immediately on the first change, then at most once per interval under continuous updates, with a trailing call when updates stop. Each fire does `m.current?.abort(); new AbortController`, and the abort handler calls `child.kill()` (default SIGTERM, direct child only). A timeout also calls `child.kill()` and the timed-out output is discarded (`Status line command timed out`, logged once).
- The promise resolves on the child's `close` event (after stdio closes), not on `exit`: a detached grandchild that inherited stdout/stderr keeps `close` pending and the result never arrives. Runs are not serialized (a new run starts regardless), so D-13's reason is better stated as: **stdio of any refresher must be DEVNULL and the refresher must be in its own session**, otherwise the line never updates and the refresher is not guaranteed to survive. (CONTEXT says the CLI "waits for its close event" before the next run; it does not - the next run starts immediately, but the *result* of the pipe-holding run is lost.)
- Output rules: `stdout` with `\r` removed and trailing `\n`s trimmed; if non-empty OR exit code 0 the text is set (exit 0 with empty output clears the line); non-zero exit with empty stdout keeps the previous text and logs once; spawn error keeps the previous text; aborted runs are ignored. When no command is configured the hook cancels and clears.
- **Inferred (not observed live):** that ANSI SGR and multi-line output render as the bundled `statusline` skill documents; real cadence during streaming; whether `/dev/tty` is openable from the piped spawn (the child inherits the parent's controlling terminal, no `setsid`).

### 4.3 Config and auth files [VERIFIED: bundle `index.js`]
- `statusLine` is an optional key of the CLI config schema (`statusLine:a.optional()`), `a` as quoted in plan 23-11. The schema is a plain `z.object` (not `.strict()`), so unknown sibling keys are stripped on parse - **inferred** that the CLI preserves unknown keys when it rewrites `cli-config.json`; D-23's "semantic preservation + re-read before replace" covers both cases. A wrong-shaped `statusLine` (bare string) is a schema error in the CLI; how the CLI degrades is unobserved.
- Config dir resolver: `CURSOR_CONFIG_DIR` if non-blank, else non-blank `XDG_CONFIG_HOME` + `/cursor`, else `~/.cursor` (`../cursor-config/dist/paths.js`, no platform gate) - matches D-21 and `tools/config_doctor_checks.py:68-86`. Data dir (`projects/`) is `CURSOR_DATA_DIR` or `~/.cursor`, independent of the config dir.
- `auth.json` path (`getAuthFilePath(app)`): win32 `%APPDATA%/<App>/auth.json`; darwin `~/.<app>/auth.json`; otherwise `${XDG_CONFIG_HOME or ~/.config}/<app>/auth.json` with `app = "cursor"` - independent of `CURSOR_CONFIG_DIR` (confirms D-14's "agent stays logged in" and D-15's mirror). Keys written: `accessToken`, `refreshToken`, `apiKey`, `bedrockCredentials`. **New fact vs D-15:** the file may carry an `apiKey` instead of an OAuth `accessToken`, and `bedrockCredentials` holds AWS secrets, so `cursor_quota` must read exactly one key by name, never log/serialize the parsed dict, and treat "no usable `accessToken`" as a defined `auth_unsupported` state (Open Question 4). `writeAuthData` is `writeFile(path, JSON, {mode: 384})` + `chmod` - **non-atomic truncate-then-write**, so a concurrent reader can see an empty or partial file: D-15's "parse error is a transient network_error" is required, not optional.

### 4.4 Dashboard logic (`./src/usage/usage-data.ts`, same bundle) [VERIFIED: bundle]
`getCurrentPeriodUsage` required; `getHardLimit` and `getPlanInfo` wrapped to `undefined` on failure; CLI call timeout 10 000 ms each; the three calls run concurrently. `c(e)=e/100` cents -> dollars; reset label from `billingCycleEnd` (fallback `planInfo.billingCycleEnd`), formatted in UTC by the CLI. Included percents: `totalPercentUsed` from `d({percentage, used: includedSpend, limit})` = `percentage` if defined else `used/limit*100` if `limit > 0` else `0`; `autoPercentUsed ?? 0`, `apiPercentUsed ?? 0`. On-demand classification `u({currentUsage, hardLimit})` exactly as D-10 describes (`individualLimit` cents > 0 -> fixed, `== 0` -> disabled; `limitType == "team"` branch; `noUsageBasedAllowed` -> disabled; `hardLimit >= 2147483647` -> unlimited/personal; `hardLimit > 0` -> fixed; else disabled; `hardLimit` undefined and no individual limit -> unavailable). Missing `planUsage` -> enterprise spend view or "not available". `included_usage_period` exists in the proto descriptors (bundle `index.js`) but is not used by the `/usage` view, so D-09's window derivation is **inferred** until the spike records a real value.
- Transport used by the POC and confirmed working live: `POST {endpoint}/aiserver.v1.DashboardService/<Method>`, headers `Authorization: Bearer <token>`, `Content-Type: application/json`, `Connect-Protocol-Version: 1`, empty JSON body `{}` [VERIFIED: POC `tools/cursor-status-line-poc.py` fetch_quota headers + POC FINDINGS "Connect-JSON POST empty body"]. Default endpoint `https://api2.cursor.sh`; `CURSOR_API_ENDPOINT` is the CLI's own override. camelCase response keys were observed live ("camelCase fields present in live responses"); keep D-12's `_pick` camel/snake lookup.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`urllib.request`, `json`, `os`, `tempfile`, `subprocess`, `http.server` in tests) | 3.14.7 on this machine; target `py312` per pyproject | All runtime code | AGENTS.md: runtime stays stdlib-only; hand-rolled JSONC precedent |
| `unittest` via `tools/run_unittest_parallel.py` | stdlib | All tests | Existing runner groups (`unit`, `unit-uv`, `integration`, `e2e`, `arch`) |
| `ast` | stdlib | Audit generator, arch rules, conformance check | `tests/test_arch.py` precedent |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `textual` (dev/wizard only) | 8.2.7 in the project venv [VERIFIED: local run] | Wizard PTY/`uv run` verification | Plan 23-17 only; never in render path |
| `ruff~=0.14`, `pylint~=4.0`, `pyright~=1.1`, `vulture~=2.14`, `shellcheck` 0.11.0 | per `uv.lock` | `make validate` | Every plan; new modules need `max-args=5` / `max-branches=12` compliance |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `urllib` + custom opener | `requests`/`httpx` | Forbidden by the stdlib-only rule and 20+ ms import cost |
| Staged move with per-def AST equality | One big hand-edited move | Not reviewable by a cheap executor; no mechanical proof of purity |
| New `tests/test_arch_statusline.py` | Extend `tests/test_arch.py` | AGENTS.md says extend `test_arch.py`; a split file would also need `gen_test_groups` and avoid merge conflicts - recommend extending but serializing plans |

**Installation:** none. **Package Legitimacy Audit:** this phase installs no external packages (stdlib-only runtime; dev tools already pinned in `uv.lock`). `gsd-tools package-legitimacy` not run; nothing to gate. Packages removed: none. Packages flagged: none.

## Architecture Patterns

### System Architecture Diagram
```
Claude Code ──stdin JSON──► claude-status-line.py ─┐
Cursor CLI ───stdin JSON──► cursor-status-line.py ─┤   (thin entries; realpath dir on sys.path)
                                                   ▼
                         <host>_host.HOST  (payload adapter, segment funcs, defaults, env prefix)
                                                   ▼
        common_render.safe_render(HOST): cfg_load_config(prefix,defaults,filename) ─► build Context
              │                                   │  (try/except -> error segment, never crash)
              │             segments = common_segments ∪ HOST.segment_funcs (dup id = startup error)
              ▼
        measure ► global meta ► assemble (PINNED, right_margin from HOST) ► stdout lines

Cursor only, off the render path:
  cursor_segments ──reads──► cursor_quota.read_quota(cache only) ──► QuotaResult(state is f(cache, now))
        │ stale/absent & no live lock
        └─► spawn detached `python3 -S cursor_quota.py --refresh` (new session, stdio DEVNULL)
                 refresher: take O_EXCL lock ► validate_endpoint ► read auth.json (read-only)
                 ► 3 concurrent HTTPS calls (no redirects) ► normalize ► atomic 0600 cache ► release lock

setup.py / wizard ─► per-host detect (unset|ours|foreign) ─► atomic JSON write (re-read just before replace)
statusline-doctor.py --host ─► same reader, foreground diagnostic, confidence label
```

### Recommended Project Structure
```
tools/
  common_types.py|common_config.py|common_probe.py|common_fmt.py|common_render.py|common_segments.py
  claude_payload.py|claude_probes.py|claude_segments.py|claude_host.py|claude-status-line.py
  cursor_payload.py|cursor_quota.py|cursor_segments.py|cursor_host.py|cursor-status-line.py
  claude-statusline.toml.sample|cursor-statusline.toml.sample|segments_inventory.toml (per-host line)
tests/
  test_status_line.py (loaders only changed)  test_status_line_golden.py  test_statusline_audit.py
  test_cursor_quota*.py  test_cursor_status_line.py  fixtures/cursor_quota/  fixtures/golden/
```

### Pattern: pure-move conformance
**What:** a script that, for every non-deleted audit row, asserts `ast.dump(moved_def) == ast.dump(base_blob_def)` (modulo the allowed call-site rewrite `fn(...)` -> `probe.fn(...)` for patched probes) and that the module exists in the row's target. **When:** every move plan. **Why:** gives a cheap executor and a cross-AI reviewer a mechanical purity proof instead of reading 2600 lines.

### Anti-Patterns to Avoid
- **Re-export facade** (`from common_fmt import *` in the old file): patches would hit the wrong module (D-05).
- **Editing golden `expected.txt` to make a move pass.** New behavior gets a new fixture.
- **Importing networking at module top in `cursor_quota`** (adds ~20 ms to a 40 ms render; D-04).
- **Passing `HOST` into `cfg_*`** (re-creates the `common_render`/`common_config` cycle; pass primitives).
- **Letting the render path call `cursor_quota` fetch code** - render calls `read_quota` (cache only).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic JSON write / three-state read | new writer | `_atomic_write_json`, `_read_json_checked` | Failure-injection tested, copies mode, never corrupts |
| Cursor config dir resolution | third resolver | factor `config_doctor_checks.py:68-86` into the new `Paths` field | Already matches the bundle |
| Per-host hook detection precedent | new detection idiom | `wire_hook_cursor` "no parent dir -> skip" rule | Same semantics, tested |
| Segment header regex, TOML load, binding | duplicate in setup | the `common_config` copy (Open Question 2) | Drift tests already exist |
| Redirect refusal | pre-check of `Location` | `HTTPRedirectHandler.redirect_request` returning `None` | Stock urllib forwards `Authorization` and turns POST into GET (D-15 experiment) |
| Lock + single-flight | pid files without expiry | `O_EXCL` lock with pid + start time + expiry | Killed refresher must not wedge refreshes |
| Concurrent create-if-absent | `isfile` then `open("w")` | the D-19 helper (link + `FileExistsError`) | Current `copy_recipe_if_absent` is racy |

## Runtime State Inventory (rename/migration)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `~/.config/ai-kit/statusline.toml` on every existing install (user content); `.bak` from `_recover_incompatible_config` | Data migration: move to `claude-statusline.toml` when destination absent; both present -> warn, change nothing (R3) |
| Live service config | Claude `settings.json` `statusLine.command` = `python3 -S <install>/tools/status-line.py` | Data migration: anchored rewrite to `claude-status-line.py`; foreign commands untouched |
| OS-registered state | None - Claude/Cursor hold the command string in their own config only; no launchd/systemd/cron entries found in the repo (`rg` for registration code in `tools/` shows none) | None |
| Secrets/env vars | `CC_AI_KIT_*` env overrides keep working for Claude (names unchanged); new `AI_KIT_CURSOR_*` for Cursor; `CURSOR_API_ENDPOINT` read-only | Code edit only |
| Build artifacts | `tools/__pycache__/status-line*.pyc` stale after the rename; installs are git clones so the old `tools/status-line.py` disappears on pull (the accepted gap) | None beyond the migration; document the re-run requirement in README |

## Common Pitfalls

1. **Oracle blind spots.** The existing golden strips ANSI and has no `effort`/`todo`/`lines`/cost payloads - a color or escape regression passes it. Avoid: new oracle compares raw bytes for all segments on (plan 23-01). Warning sign: the oracle fixtures have fewer segments than `SEGMENTS`.
2. **"Pure move" that isn't.** `Context` field removal, `HOST.env_prefix`, registry discovery and `BUILDERS` removal change code. Keep them in plan 23-08 with the oracle as guard.
3. **Patch targets after the move.** `patch.object(sl, "probe_git_snapshot")` (13 uses) patches the namespace the caller reads; after the move the caller is in another module. Use module-attribute access for patched probes (plan 23-05).
4. **`test_arch.py` import-time coupling.** It loads `tools/setup.py` at import (:40-43) and `TestSegmentInventory` loads `status-line.py` by path; the rename breaks both in one commit. The rule-9 broad-except allowlist is keyed on `("tools/status-line.py", "core_safe_build"|"safe_render")`.
5. **Kill semantics.** SIGTERM reaches only the direct child; a Python render killed mid-flight leaves a lock it took. Lock records pid + start time and expires; refresher in a new session with DEVNULL stdio or the line never updates (4.2).
6. **`auth.json` torn read** (non-atomic CLI write) and **`apiKey`-only logins** (4.3).
7. **Inline-fetch drift.** A 1.9 s cold fetch (POC) vs a 300 ms `maxWait` means any blocking fetch is killed on every update during streaming; render p50 is ~40 ms so only the cache read fits.
8. **Provider env/namespace collision** (`AI_KIT_CURSOR_SEGMENT_*` used for both toggles and provider mirror) - Open Question 1.
9. **Bool-as-number and string epoch ms** in Dashboard JSON (D-10): `isinstance(True, int)` is true in Python; reject bools explicitly; proto3 JSON may encode int64 as strings.
10. **Wizard preview** must never reach the network: preview uses a synthetic cache in a temp `XDG_CACHE_HOME` and an environment with no auth path (D-24); assert no `cursor_quota` fetch function is called.
11. **Generated test-group listing** in `Makefile`/`.pre-commit-config.yaml`: adding/removing test modules without `tools/gen_test_groups.py` fails `test_gate_scope`.
12. **Cursor 'unavailable' vs 'disabled'**: a failed `GetHardLimit` must be `unavailable`, never `disabled` (D-10); test with the fake server returning 500 for that method only.

## Code Examples

### Redirect refusal (D-15) - stdlib shape
```python
# Source: CPython urllib.request.HTTPRedirectHandler contract (redirect_request may return None)
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None  # urllib then raises HTTPError(3xx); map to network_error, never follow
```

### Create-if-absent (D-19)
```python
# Source: D-19 spec; os.link fails with FileExistsError atomically if dest exists
def create_if_absent(dest: str, data: bytes) -> bool:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest) or ".")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data); fh.flush(); os.fsync(fh.fileno())
        try:
            os.link(tmp, dest)
        except FileExistsError:
            return False                      # winner already there
        except OSError:                       # FAT/FUSE/NFS: no hard links
            efd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(efd, "wb") as fh:
                fh.write(data)
        return True
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
```

### Runner-simulator core (test helper)
```python
# Source: bundle use-status-line.ts semantics (4.2): argv spawn, JSON on stdin, SIGTERM to direct child only
proc = subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=workdir, env=env)
proc.stdin.write(json.dumps(payload).encode()); proc.stdin.close()
time.sleep(kill_after_s); proc.terminate()       # direct child only, no process-group kill
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Design 5.2 on-demand ramp (50/80) | Shared 5/10/15 gap gauge on both hosts | ROADMAP 2026-10-13, SPEC | Cursor segments use `util_window_gap` |
| POC blocking sync fetch | Cache-only render + detached refresher | D-13 | Render never waits on network |
| One status-line flow in wizard | Host-keyed `HostView`s | D-22 | Both hosts in one app |
| Claude-only `--with-statusline` | `nargs="?"` per-host | D-23 | Bare flag now wires every detected host (README must call out) |

**Deprecated/outdated:** `docs/architecture/status-line-pipeline.md` (deleted, D-04); the 2026.10.01 bundle citations (re-verified on 10.14).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The CLI preserves unknown keys in `cli-config.json` on rewrite (zod object is non-strict) | 4.3 | Low; D-23 re-read + semantic preservation covers both |
| A2 | ANSI and multi-line stdout render in the Cursor TUI as the bundled skill documents | 4.2 | Medium; spike/live run confirms; Cursor line design assumes SGR works |
| A3 | `/dev/tty` is openable from the CLI's piped spawn | 4.2 | Low-medium; affects terminal-size probing; fall back to `render_width_chars` |
| A4 | `included_usage_period` semantics (MONTHLY/WEEKLY/UNSPECIFIED) match D-09 | 4.4 | Medium; owner spike records the real value; underivable window renders neutral |
| A5 | `param_summary` carries a reasoning-effort-like string for parameterized models | 4.1 | Low; segment is conditional |
| A6 | apiKey-only logins cannot use the Dashboard bearer path | 4.3 | Medium; define `auth_unsupported` and hide quota |
| A7 | Detached refresher outlives the CLI's SIGTERM when started with `start_new_session=True` | 2/3 | Low; testable with the runner simulator |
| A8 | The decision-rule thresholds in section 3 (p95 + render < min gap and < 300 ms) are acceptable to the owner | 3 | Low; owner may tighten |
| A9 | A cheap executor can finish each plan in section 2 inside 3600 s | 2 | Medium; 23-06 is the likely overrun - pre-split into 06a/06b |

## Open Questions

1. **Provider env vs toggle env prefix collision (D-18 vs D-20).**
   - Known: Claude uses `CC_AI_KIT_SEGMENT_<KEY>` (toggles) vs `AI_KIT_SEGMENT_{COLS,ID,LINE,POSITION}` (provider mirror), distinct prefixes. Both Cursor names are specified as `AI_KIT_CURSOR_SEGMENT_*`.
   - Unclear: which wins for segment ids `cols`, `id`, `line`, `position`.
   - Recommendation: name the Cursor provider mirror `AI_KIT_CURSOR_PROVIDER_{COLS,ID,LINE,POSITION}` (leave toggles as D-20) and add a test; amend D-18 text. Needs owner confirmation because D-18 is locked wording.
2. **Does `setup.py` keep duplicating segment defaults/regex or import them?** Comment at `setup.py:92-95` says duplication is deliberate (wizard must run while the renderer is mid-edit); design 6.2 says delete it; D-03 says lazy host imports. Recommendation: lazy import of `common_config`/`*_host` in the functions that need them (one source of truth) plus keep the drift tests as import-equality tests.
3. **History allowlist for the anchored reference check.** Extend to `docs/refactor/**` and `docs/wizard-redesign/**` (historical mockups/triage) or edit them? Recommendation: allowlist both; edit only live code, README, AGENTS.md and comments.
4. **`apiKey`/`bedrockCredentials` in `auth.json` (new in this research).** Recommendation: read only `accessToken`; absent -> `auth_unsupported` (quota hidden, doctor explains); never log the parsed dict.
5. **Spike gating vs AGENTS.md.** CONTEXT says Part B waits on the spike; recommendation is two planning slices (section 2). If the owner prefers a single `/gsd-plan-phase` run, add an explicit `checkpoint:human-action` plan holding the spike record and keep 23-12..18 `depends_on` it.
6. **Where does the spike record live?** SPEC R5 says "the phase RESEARCH"; recommendation is `23-SPIKE.md` and a one-line SPEC/ROADMAP amendment (AGENTS.md: amend formally when a live fact contradicts wording).
7. **Does the golden need to cover `render_time`/`slowest`?** They are time-dependent; recommendation: exclude from byte-identity, cover with the existing structural tests, and add one deterministic-clock test via `t_start` injection if the plan wants them in the oracle.
8. **Unobserved at spike time:** whether the CLI mutates `auth.json` (token refresh) while the refresher reads it - owner reports; code already tolerates torn reads.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | everything | ✓ | 3.14.7 (target py312) | - |
| uv + project venv (textual) | wizard `uv run`, dev tools | ✓ | uv 0.11.28, textual 8.2.7 | - |
| node | e2e tests that run gsd-core | ✓ | v24.21.0 | - |
| shellcheck | `make lint` | ✓ | 0.11.0 | - |
| ruff (system) | `make format/validate` | ✗ on PATH | - | `uv run ruff` via project venv |
| rg, bat, codegraph | exploration | ✓ | - | grep/sed |
| `cursor-agent` | owner live runs only | ✓ installed (2026.10.14-941492e); NOT executed in this research | - | loopback fake + runner simulator for all automated tests |
| Cursor login / quota / network | spike, R12 live run | owner-only | - | none (runbook) |

**Missing dependencies with no fallback:** the owner's Cursor login and quota (spike items 1-3, R12 live run) - handled by runbook + checker.
**Missing with fallback:** system `ruff` (use `uv run`).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` through `tools/run_unittest_parallel.py` (groups `unit`, `unit-uv`, `integration`, `e2e`, `arch`) |
| Config file | `pyproject.toml` (ruff/pylint/pyright/vulture), generated group listing in `Makefile` and `.pre-commit-config.yaml` |
| Quick run command | `python3 -m unittest tests.test_status_line tests.test_status_line_golden tests.test_arch tests.test_statusline_doctor -q` (~2-3 s today) |
| Full suite command | `make test` then `make validate` |

### Phase Requirements -> Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| STL-01 | 182-row audit == AST count; every non-deleted row exists in its target | unit | `python3 -m unittest tests.test_statusline_audit` | ❌ Wave 0 (23-01) |
| STL-01 | Claude render byte-identical (raw ANSI, all segments) | unit | `python3 -m unittest tests.test_status_line_golden` | ❌ Wave 0 (23-01) |
| STL-01 | Entry-level subprocess render identical before/after | e2e | same module | ❌ Wave 0 |
| STL-01 | Moved defs AST-equal to base blob | unit | `tests.test_statusline_audit` conformance class | ❌ Wave 0 |
| STL-01 | Dependency-direction + banner/prefix rules, each with a non-vacuity twin | arch | `python3 -m unittest tests.test_arch` | ✅ extend |
| STL-01 | Migration: old->new, second run no-op, both-present warns, foreign untouched | unit | `tests.test_setup` (new class) | ✅ extend |
| STL-01 | Reference check `rg -P` with allowlist | unit | new test or `tests.test_arch` | ❌ Wave 0 (23-07) |
| STL-02 | Gauge boundaries 5/11/15/15.01, uncomputable -> white no sign, Cursor segments import the same function | unit | `tests.test_status_line` + `tests.test_cursor_status_line` | ❌ (23-09/15) |
| STL-02 | Per-segment synthetic payload tests: null/absent fields, 4 on-demand states, `render_width_chars` precedence, `≈` | unit | `tests.test_cursor_status_line` | ❌ (23-15) |
| STL-02 | Strict provider sees identical stdin/env/cache path | unit | golden strict-provider capture | ❌ (23-01, 23-16) |
| STL-03 | Normalization tables: cents/dollars, string epoch ms, bool rejected, unlimited sentinel, derive-else-hide | unit | `tests.test_cursor_quota` | ❌ (23-12) |
| STL-03 | Transport: http, foreign host, userinfo, port, cross-origin redirect all refused; token never in cache/log/argv/env | unit + loopback | `tests.test_cursor_quota_transport` | ❌ (23-13) |
| STL-03 | Only `cursor_quota` imports networking, and only inside functions (AST) | arch | `tests.test_arch` | ❌ (23-13) |
| STL-03 | Fresh/stale/negative, 401/403, `now == cycle_end`, timeout, killed refresher, concurrent renders, env isolation | unit/e2e | `tests.test_cursor_quota_cache` + runner simulator | ❌ (23-14) |
| STL-04 | Spike record present, checker passes on owner bundle, decision rule verdict recorded | gate | `python3 tmp/spike/spike_check.py` (promoted to `tests/` helper) | ❌ (23-02) |
| STL-05 | Detect/wire matrix 3x2x2, semantic preservation, per-host uninstall, failure-injected TOML writes, 16-process create-if-absent race | unit | `tests.test_setup` | ✅ extend |
| STL-05 | Two-host wizard sequence | PTY | `tests.test_wizard_pty` (+ `uv run` manual) | ✅ extend |
| STL-05 | Doctor `--host claude|cursor` fetch status + confidence | unit | `tests.test_statusline_doctor` | ✅ extend |

### Arch-rule non-vacuity (each new rule needs a snippet that must fail)
Common imports a host module; claude imports cursor (and vice versa); a non-entry/setup/wizard/doctor module imports `*_host`; a `*_host` env prefix literal outside `*_host.py` (rule 1 reworded); duplicate segment id across `common_segments` and a host; module-level `import urllib.request`/`socket`/`http.client` in any non-`cursor_quota` module and at top level of `cursor_quota`; per-module banner role-prefix violation; `shell=True`; a new `except Exception` without allowlist entry (rule 9 keys updated to new paths).

### Sampling Rate
- **Per task commit:** the quick run command above plus the plan's own module.
- **Per wave merge:** `make test-unit arch-test` (+ `e2e-test` when entries or setup change).
- **Phase gate:** `make test` and `make validate` green, `uv run python tools/wizard_app.py` exercised, `/gsd-secure-phase`.

### Wave 0 Gaps
- [ ] `tests/test_status_line_golden.py` + extended fixtures (raw-ANSI, all-segments, entry subprocess, strict-provider capture)
- [ ] `tests/test_statusline_audit.py` + generator and committed table
- [ ] Spike tooling: fake Dashboard server, runner simulator, `spike_check`, runbook
- [ ] `tools/gen_test_groups.py` refresh after each new test module

## Security Domain

### Applicable ASVS Categories (level 1, `security_enforcement` on)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (bearer reuse) | Read `accessToken` read-only from the CLI's `auth.json`; never refresh/write/persist |
| V3 Session Management | no | - |
| V4 Access Control | partial | Cache/lock files 0600 under the user's cache dir; refuse to follow symlinked cache dirs not owned by the user |
| V5 Input Validation | yes | Strict payload/Dashboard-JSON parsing (reject bool/NaN/negative), endpoint validator, TOML bad value -> error segment |
| V6 Cryptography | yes (transport only) | Default TLS verification via stdlib; no custom crypto, no cert pinning, no `verify=False` |
| V8 Data Protection | yes | Token never on argv/env/logs/cache; cache holds derived numbers only |
| V9 Communications | yes | HTTPS only, hostname `cursor.sh`/`*.cursor.sh` exact dot-boundary suffix, port 443, no userinfo, no redirects |
| V12 Files | yes | Atomic writes, race-safe create-if-absent, `O_EXCL` lock |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Bearer forwarded on redirect (urllib forwards Authorization, POST->GET) | Information disclosure | Redirect handler returns `None` (D-15) |
| `CURSOR_API_ENDPOINT` pointed at attacker host | Information disclosure | `validate_endpoint` before token read; test `cursor.sh.evil.com` |
| Token leakage via cache/log/argv/env or parsed dict | Information disclosure | Single-module boundary, arch test that no other module imports networking, fake-server assertion that the token is absent from every written file |
| Foreign `statusLine` overwritten headless | Tampering | Classification + refuse-headless; test per host |
| Torn `cli-config.json` rewrite race with the CLI | Tampering/DoS | Re-read + re-classify immediately before atomic replace (D-23) |
| Stale lock wedging refresh / lock-file DoS | DoS | Expiring `O_EXCL` lock with pid + start time |
| Credential-bearing leftovers (POC `tmp/cli-config.json.bak` 0644 with `authInfo`) | Information disclosure | D-12 deletion step, tracked in 23-02/23-18 |

## Sources

### Primary (HIGH confidence)
- `tools/status-line.py`, `tools/setup.py`, `tools/wizard_app.py`, `tools/statusline-doctor.py`, `tools/config_doctor_checks.py`, `tests/test_status_line.py`, `tests/test_arch.py`, `tests/wizard_fixtures.py`, `tools/gen_test_groups.py` - read this session (AST recomputation, line anchors).
- Installed `cursor-agent` bundle `2026.10.14-941492e` (`7000.index.js`, `index.js`): payload builder, `use-status-line.ts`, `use-debounced-callback.ts`, `usage-data.ts`, `paths.js`, `getAuthFilePath`, `writeAuthData`, config zod schema. Probed 2026.10.01 and 2026.09.15 for contract continuity.
- POC worktree `poc/cursor-statusline`: `tmp/cursor-statusline-poc-FINDINGS.md`, redacted `tmp/cursor-payload.json`, `tools/cursor-status-line-poc.py` (headers, redirect check). Credential-bearing POC files were not opened.
- `23-SPEC.md`, `23-CONTEXT.md`, `.planning/specs/2026-10-10-host-split-statusline-design.md`.

### Secondary (MEDIUM confidence)
- Local measurements (render and import latency, sibling import under `-S`, baseline test run) on Python 3.14.7.

### Tertiary (LOW confidence)
- Anything under `[ASSUMED]`/Assumptions Log; no web sources were used (the bundle is the first-party source).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib-only mandate, no new packages.
- Architecture/split: HIGH for counts and anchors; MEDIUM for plan sizing (A9).
- Cursor contract: HIGH for runner/payload/auth/config (bundle source), MEDIUM for Dashboard behavior (one POC run), LOW for cadence/latency/token lifetime.
- Pitfalls: HIGH for split/test coupling, MEDIUM for transport/lock edge cases.

**Research date:** 2026-10-23
**Valid until:** 2026-11-06 (Cursor CLI ships fast-moving versions; re-check the bundle contract at spike time per CONTEXT)
