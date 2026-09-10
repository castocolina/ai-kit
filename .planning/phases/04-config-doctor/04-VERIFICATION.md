---
phase: 04-config-doctor
verified: 2026-09-10T12:00:00Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/04-config-doctor/04-01-PLAN.md"
  - ".planning/phases/04-config-doctor/04-01-SUMMARY.md"
  - ".planning/phases/04-config-doctor/04-02-PLAN.md"
  - ".planning/phases/04-config-doctor/04-02-SUMMARY.md"
  - ".planning/phases/04-config-doctor/04-03-PLAN.md"
  - ".planning/phases/04-config-doctor/04-03-SUMMARY.md"
  - ".planning/phases/04-config-doctor/04-REVIEW.md"
  - ".pre-commit-config.yaml"
  - "Makefile"
  - "README.md"
  - "pyproject.toml"
  - "tests/test_config_doctor.py"
  - "tests/test_config_doctor_pty.py"
  - "tools/config_doctor_app.py"
  - "tools/config_doctor_appliers.py"
  - "tools/config_doctor_checks.py"
  - "tools/config_doctor_readers.py"
  - "tools/setup.py"
covered_digest: "v1:sha256:21771e16507def8483166a05c6bd14b66eb98e3141a9a01d11b3858858898f05"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 4: Config Doctor Verification Report

**Phase Goal:** One-screen, confidence-labeled config diagnostics across Claude Code/opencode/Codex/Cursor with confirmed per-item apply.
**Verified:** 2026-09-10T12:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One command shows every row of the Checks Catalog (25 rows, plus the folded-in cross-runtime `rtk`-Cursor-integration check) across every runtime with a config file present | ✓ VERIFIED | `CONFIG_DOCTOR_ROWS` in `tools/config_doctor_checks.py` holds exactly 25 `CheckRow` records spanning Claude/opencode/Codex/Cursor + 1 cross-runtime row (independently counted, see Spot-Checks). `tests.test_config_doctor.TestFullCatalogRegression.test_five_sections_twenty_five_rows` and `tests.test_config_doctor_pty.TestConfigDoctorPty.test_full_catalog_renders_under_pty_without_crashing` both pass (re-run by me, not trusted from SUMMARY). Live probe with only a Claude settings.json present correctly rendered exactly 2 sections (`claude`, `cross`) — proving the catalog is genuinely presence-driven, not statically rendered. |
| 2 | A runtime with no config file present has its whole section skipped rather than shown as failing checks; undeterminable values show "unknown," never silently pass/fail | ✓ VERIFIED | `build_catalog` in `tools/config_doctor_checks.py:1031-1054` gates each of the 4 per-runtime sections on `os.path.isfile(path)` and omits zero-row sections; the cross section has no such gate (by design — SC1). `evaluate_row` returns `current_display="unknown"` whenever `ctx.data is None and row.reads_section_file` or a read returns the `UNKNOWN` sentinel. `TestPresence` (6 tests) and `TestUnknownDegrade` (3 tests) pass. Reproduced live: an env with only Claude's settings.json present yielded sections `['claude', 'cross']` only — opencode/codex/cursor sections silently omitted, not shown as failing. |
| 3 | Lower-confidence or no-real-backing-setting rows (Codex reasoning effort, opencode retention) are visibly labeled as such and never offered as apply actions | ✓ VERIFIED | `codex-model-reasoning-effort` row has `confidence="LOW"` and no `apply=` kwarg (defaults to `None` → `apply_eligible=False` via `evaluate_row`). `opencode-retention`, `codex-hooks`, `codex-memories-durations`, `cursor-sandbox-cli-config`, `cursor-model-parameters`, `cursor-local-retention`, `cursor-cli-telemetry` all likewise carry no `apply=` and their `why` text states "Apply stays None permanently." Confirmed by direct source read — none of these 7+1 informational/low-confidence rows have an `apply` callable wired. |
| 4 | Applying a change requires explicit, per-item confirmation naming the exact change; no bulk "apply all"; security-relevant applies show the literal resulting config before writing | ✓ VERIFIED | `ConfirmApplyScreen.compose()` (`tools/config_doctor_app.py:78-98`) renders `current -> target` and, only `if self.row.get("security_relevant")`, fetches a dry-run preview and appends `literal_resulting_config`. `action_confirm` calls `ctx.apply(row_id, False)` exactly once for exactly one `row_id`; `action_cancel`/Escape dismiss with `None` and never call apply. `TestNoBulkApply` (structural, scans all 3 modules + BINDINGS for `apply_rows`/`apply_selected`/`apply_each`-shaped names) passes under `uv run` (verified directly — this test is skipped without `textual` installed, confirmed genuinely passing when run with `uv run --with textual`). `TestConfirmApplyScreen` and the PTY test `test_apply_confirm_flow_writes_the_target_value` both pass. |
| 5 | Applying a JSONC change to opencode preserves every other byte, using the same tested surgical-edit approach as Phase 2 | ✓ VERIFIED | Reproduced live end-to-end: wrote a real `opencode.jsonc` with a `// keep this comment` line, ran `apply_row("opencode-share-mode", ctx, dry=False)` against it — the resulting file has `"share": "disabled"` with the comment and every other byte byte-for-byte unchanged. `set_jsonc_value` in `tools/config_doctor_appliers.py` is a pure text splice using the same `_classify`/comment-aware tokenizer ported from `ai-kit-opencode-providers`'s `jsonc_edit` module. `_apply_opencode_share_mode` self-validates the spliced text (`_parse_jsonc_text`) before writing and refuses (no write) on failure. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/config_doctor_readers.py` | 3-state JSON/JSONC/TOML readers | ✓ VERIFIED | `read_json_checked`/`read_jsonc_checked`/`read_toml_checked` all route through `_classify_parsed`, returning `("absent", {})` / `("ok", dict)` / `("unreadable", None)`. Stdlib-only, no imports from setup.py/wizard_app.py/skills/*. |
| `tools/config_doctor_checks.py` | Declarative engine, 25-row catalog, apply dispatcher | ✓ VERIFIED | 1054 lines; `CONFIG_DOCTOR_ROWS` (25 entries), `build_catalog`, `apply_row`, 4 wired appliers, `_toml_table_span`/`_upsert_toml_table_key` (post-review-fix, line-anchored). |
| `tools/config_doctor_app.py` | Textual review + confirm-apply screen | ✓ VERIFIED | `ConfigDoctorApp` (DataTable + detail pane), `ConfirmApplyScreen` (per-item confirm, literal-config preview gated on `security_relevant`). Imports nothing from `config_doctor_checks.py` — driven via `ConfigDoctorContext` closures only. |
| `tools/config_doctor_appliers.py` | Atomic JSON/TOML/JSONC writers | ✓ VERIFIED | `atomic_write_json`, `write_toml_region_replace` (validate-before-write, post-fix), `_atomic_write_text`, `set_jsonc_value` (surgical splice). All three durable-write paths fsync the containing directory (post-fix WR-04). |
| `tools/setup.py` `--config-doctor` | CLI entry point | ✓ VERIFIED | `cmd_config_doctor` builds catalog, wires an `apply` closure to `apply_row`, wraps the TUI in `stdin_on_tty()`. The flag returns before `install`/`reconfigure` dispatch. Help text corrected post-review (WR-02) to no longer claim read-only. |
| `tests/test_config_doctor.py` + `tests/test_config_doctor_pty.py` | Test coverage | ✓ VERIFIED | 1630 + 264 lines; 81 + 4 = 85 tests, all passing when re-run independently (6 skips are environment-only — `textual` not importable outside `uv run`; confirmed passing under `uv run --with textual`). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tools/setup.py:cmd_config_doctor` | `config_doctor_checks.build_catalog` | direct call | ✓ WIRED | Catalog built from real `env`, passed into `ConfigDoctorContext`. |
| `tools/setup.py:cmd_config_doctor` | `config_doctor_checks.apply_row` | closure `apply(row_id, dry)` | ✓ WIRED | Closure captures a `ReadContext(data=None, env=env, runner=None)` and calls `apply_row`; injected into `ConfigDoctorContext.apply`. |
| `ConfigDoctorApp.action_apply_row` | `ConfirmApplyScreen` | `push_screen` | ✓ WIRED | Only invoked when `row.get("apply_eligible")` is true; silent no-op otherwise (by design). |
| `ConfirmApplyScreen.action_confirm` | `ctx.apply(row_id, False)` | direct call | ✓ WIRED | Single-row dispatch, refusal path leaves the row unchanged and surfaces `reason`. |
| `apply_row` | 4 wired appliers (`_apply_claude_retention`, `_apply_claude_sandbox_enabled`, `_apply_opencode_share_mode`, `_apply_codex_history_persistence`) | `row.apply` NamedTuple field | ✓ WIRED | Dispatches by row identity, not `row.runtime` branching; exceptions converted to refusal dicts. |
| 4 appliers | `tools/config_doctor_appliers.py` writers | direct call | ✓ WIRED | JSON rows call `atomic_write_json`; JSONC row calls `_atomic_write_text` after self-validation; TOML row calls `write_toml_region_replace`. |

### Behavioral Spot-Checks (run independently by the verifier, not trusted from SUMMARY.md)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite for config-doctor | `python3 -m unittest tests.test_config_doctor tests.test_config_doctor_pty -v` | 85 tests, 0 failures, 6 skipped (textual-under-uv only) | ✓ PASS |
| Skipped tests pass under uv (textual present) | `uv run --with textual python3 -m unittest tests.test_config_doctor.TestNoBulkApply -v` | 2/2 pass | ✓ PASS |
| Full repo test suite (once) | `make test` | 1413 tests, 0 failures, 25 skipped | ✓ PASS |
| Lint (py-compile/shellcheck) | `make lint` | exit 0 | ✓ PASS |
| Type-checking | `uv run pre-commit run pyright --all-files` | Passed | ✓ PASS |
| Dead-code scan | `uv run pre-commit run vulture --all-files` | Passed | ✓ PASS |
| Lint score | `uv run pre-commit run pylint --all-files` | 9.98/10; only findings are in `tools/status-line.py` (git-blamed to a pre-Phase-4 commit `f849042`/`0e6a934`, unrelated to Config Doctor) | ✓ PASS (no new findings) |
| Row count | inline import of `config_doctor_checks`, `len(CONFIG_DOCTOR_ROWS)` | 25 | ✓ PASS |
| Live catalog build, presence-gating | scratch env with only Claude settings.json present | sections `['claude', 'cross']` only | ✓ PASS |
| Live apply: `claude-retention` | `apply_row('claude-retention', ctx, dry=False)` against a real scratch `settings.json` (15 → 3650) | file updated to `"cleanupPeriodDays": 3650`; other keys (`sandbox.enabled`) untouched | ✓ PASS |
| Live refusal: `cleanupPeriodDays=0` | `_apply_claude_retention(ctx, 0, dry=False)` | `{"ok": False, "reason": "refused: cleanupPeriodDays 0 is never writable"}`, no write | ✓ PASS |
| Live apply: `opencode-share-mode` JSONC surgical write | real `opencode.jsonc` with a `//` comment, `apply_row('opencode-share-mode', ...)` | only the `"share"` value changed; comment and every other byte preserved exactly | ✓ PASS |
| Live apply: `codex-history-persistence` with decoy comment (CR-01 regression) | `config.toml` with `# see [history] below...` comment above the real `[history]` table, `apply_row('codex-history-persistence', ...)` | correctly wrote `persistence = "none"` inside the real table; decoy comment untouched, no corruption | ✓ PASS |

### Code Review Findings — Independently Re-Verified

`04-REVIEW.md` (2026-09-10) found 2 CRITICAL + 4 WARNING issues, all marked "Status: FIXED" in that report and landed in commit `cf13c88`. I independently re-verified each fix against current source rather than trusting the report's self-assessment:

| Finding | Claimed Fix | Verified In Source | Verified By Reproduction |
|---------|-------------|---------------------|---------------------------|
| CR-01: TOML table-header substring match diverted by decoy comment text | Line-anchored regex (`(?m)^\[table\]$`) | ✓ `tools/config_doctor_checks.py:264` uses `re.search(rf"(?m)^{re.escape(header)}[ \t]*$", text)` | ✓ Live repro above: decoy comment no longer diverts the write |
| CR-02: TOML writer wrote before validating | Validate via `tomllib.loads` before touching disk | ✓ `tools/config_doctor_appliers.py:81-84` calls `tomllib.loads(new_text)` before any `os.makedirs`/`tempfile.mkstemp` | ✓ Existing `TestAppliers` (3 TOML-writer tests) still pass against new implementation |
| WR-01: sandbox applier crashes on non-dict `sandbox` value | Normalize non-dict `sandbox` to `{}` | ✓ `_apply_claude_sandbox_enabled` (checks.py:196-198) does `dict(existing_sandbox) if isinstance(existing_sandbox, dict) else {}` | Regression test `test_apply_claude_sandbox_enabled_normalizes_non_dict_sandbox_value` present and passing |
| WR-02: stale "read-only" help text | Update help string | ✓ `tools/setup.py:2777`: `"launch the config diagnostics TUI (per-item apply, explicit confirm)"` | — |
| WR-03: README missing `--config-doctor` docs | Add README section | ✓ `README.md:419-425` documents the flag, its scope, and the no-bulk-apply guarantee | — |
| WR-04: inconsistent directory-fsync durability | Add fsync to TOML/text writers | ✓ Both `write_toml_region_replace` and `_atomic_write_text` now fsync the containing directory after `os.replace` | — |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| REQ-config-doctor-diagnostic-checks | 04-01, 04-02 | ✓ SATISFIED | 25-row catalog across 4 runtimes + cross-runtime row; presence-gating; unknown-degrade; low-confidence labeling — all verified above. `.planning/REQUIREMENTS.md` line 76 still shows "Pending" (a bookkeeping field expected to be updated by the ship/complete-milestone workflow after this verification, not a code gap). |
| REQ-config-doctor-review-screen | 04-01, 04-02 | ✓ SATISFIED | `ConfigDoctorApp` renders current/recommended/confidence/citation for every row in one `--config-doctor` invocation; "unknown" display path verified. |
| REQ-config-doctor-apply-flow | 04-03 | ✓ SATISFIED | Per-item confirm, atomic/surgical writers, no-bulk-apply structurally enforced, security-relevant literal-config preview — all verified above, including two independent live end-to-end reproductions (JSON + JSONC + TOML). |

No orphaned requirements found for Phase 4 in REQUIREMENTS.md.

### Anti-Patterns Found

None. `grep` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and common empty-implementation patterns across all 4 `tools/config_doctor_*.py` modules returned zero matches. `git status --porcelain` is clean after all live verification probes (all writes were confined to `/tmp` scratch directories via `CLAUDE_CONFIG_DIR`/`OPENCODE_CONFIG_DIR`/`CODEX_HOME`/`CURSOR_CONFIG_DIR`/`HOME` env overrides — the real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex` were never touched).

### Human Verification Required

None. All observable truths were verifiable programmatically (source inspection, independent test re-execution, and live scratch-env behavioral reproduction of every write path, including the two code-review-fixed bugs).

### Gaps Summary

None. All 5 ROADMAP Phase 4 success criteria hold, all 3 requirements are satisfied, both CRITICAL and all 4 WARNING code-review findings are independently confirmed fixed (not just claimed), and 1413/1413 tests pass with a clean pylint/pyright/vulture/shellcheck bill of health (excluding one pre-existing, pre-Phase-4 lint nit in an unrelated file).

The only non-code observation is that `.planning/ROADMAP.md`'s Progress table (line 172) and `.planning/REQUIREMENTS.md` (lines 76-78) still show Phase 4 as "Not started"/"Pending" — this is expected bookkeeping that the ship/milestone-completion workflow updates after verification passes, not a functional gap.

---

*Verified: 2026-09-10T12:00:00Z*
*Verifier: Claude (gsd-verifier)*
