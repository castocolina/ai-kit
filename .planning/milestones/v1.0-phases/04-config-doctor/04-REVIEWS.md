---
phase: 04
reviewers: [opencode]
reviewed_at: 2026-09-10T02:30:41Z
plans_reviewed: [04-01-PLAN.md, 04-02-PLAN.md, 04-03-PLAN.md]
models:
  opencode: "router-env/my-plan-review (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 04

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll verify the plans' claims against the actual repo before writing the review. Let me check the current state of the phase directory and the key code references.
The plans are pre-execution (no config_doctor modules exist yet — expected for plan review). Now let me verify the key line-number claims against real source.
All cycle-2 citations verified so far. Let me do a final check of `main()`'s structure and the `_StTty`/`require_tty` names that 04-01's wiring depends on, plus confirm the 04-02 inline verify's import-resolution hazard against how the modules will be laid out.
# Cross-AI Plan Review — Phase 04 (Config Doctor), Cycle 3

**Verification method:** checked every load-bearing claim against the live repo — `tools/setup.py` (`main` argparse at 2717-2749 with the exact `cast("_StdTty", require_tty(open_tty()))` try/finally shape 04-01 mirrors, `stdin_on_tty` wrap at 2503, `import wizard_app  # pylint: disable=import-outside-toplevel` at 2482, installer's 2-step `CURSOR_CONFIG_DIR`/`~/.cursor` precedence at 57-58, `_read_json_checked` 1363, `_atomic_write_json` 1383, `read_toml` 191, `write_toml_preserving` 451, `cmd_check` 2611), `tools/wizard_app.py` (`WizardContext.commit: object = None` at 121, `WizardCrash` Textual-swallow docstring at 128-137, `run_wizard` 940), `jsonc_edit.py` (`code_indices` 285, `strip_trailing_commas` 302, `find_provider_object` 155, `remove_provider` 416), `tools/hooks/detect.py` (`RTK_PROBE_TIMEOUT_SECONDS = 2.0` at 31, `_probe_rtk_hook` 73), `03-RESEARCH.md:533/539` (the verbatim `[ok] Cursor hook: registered in hooks.json` line), `tools/hooks/README.md`'s closing fold-in line, `tests/test_wizard_pty.py` (`spawn_pty_piped_stdin` 100, `TestCurlBashE2E` 920), `tests/test_ai_kit_opencode_providers.py:14`, `Makefile:33-39`, `.pre-commit-config.yaml:27/48/53`, `pyproject.toml:87-93`. The Config Doctor modules do not exist yet (pre-execution, as expected — `git ls-files` confirms; waves 1-2's summaries are forward references filled in at execution time).

**Cycle-3 headline:** all 9 cycle-2 actionable findings are genuinely resolved in the plan text — verified below, not taken from the ledgers. I found **0 HIGH** and **1 new MEDIUM** (a spurious-failure `<verify>` command in 04-02 Task 2) plus two LOW nits. No manufactured findings.

---

## 04-01

**Summary:** A rigorously repo-grounded tracer that proves the full four-layer architecture on one real row, with all three cycle-2 findings verifiably fixed in the plan text.

**Round-2 disposition verification (all RESOLVED):**
- **MEDIUM — Cursor XDG fallback:** Task 1's `resolve_runtime_config_paths` now implements Cursor CLI's documented 3-step precedence (`CURSOR_CONFIG_DIR` → `$XDG_CONFIG_HOME/cursor` → `~/.cursor`, `/cli-config.json` appended), explicitly distinguished from `tools/setup.py:57-58`'s shorter installer precedence for `hooks.json` — which I verified is indeed exactly `env.get("CURSOR_CONFIG_DIR") or os.path.join(home, ".cursor")`. Task 2 adds the dedicated XDG-only presence test, and the acceptance criteria pin `cursor`'s value ending in `cli-config.json`. **RESOLVED.**
- **LOW — `code_indices` port dependency:** Task 1's read_first and action now both name `code_indices` (`jsonc_edit.py:285-299` — verified real) with the explicit "omitting it leaves the ported `strip_trailing_commas` raising `NameError`" rationale. **RESOLVED.**
- **LOW — pylint disable comment:** Task 1's action requires the trailing `# pylint: disable=import-outside-toplevel` on both in-body imports, mirroring the verified `tools/setup.py:2482`; acceptance criterion pins it. Verified `tools/setup.py` is inside the pylint hook's `files:` regex (`.pre-commit-config.yaml:27`). **RESOLVED.**

**Strengths:**
- The `main()` wiring spec matches the real code precisely: `cast("_StdTty", require_tty(open_tty()))` + try/finally is the actual install-branch shape at `tools/setup.py:2740-2744`; the unconditional-return requirement for the new flag is correct given `subcommand`'s `nargs="?"` default of `"install"` (`tools/setup.py:2722-2724`) — without it, `setup.py --config-doctor` would fall through into a real install run.
- The `stdin_on_tty()` wrap + piped-stdin PTY test remain the strongest cycle-1 fix; the rationale (Textual reads fd 0; a PTY always supplies one) is sound and the harness (`spawn_pty_piped_stdin`, verified at `tests/test_wizard_pty.py:100`) is real.
- `read_toml_checked`-is-new remains correctly justified: `tools/setup.py:191`'s own docstring documents the `{}`-on-any-error conflation.
- Gate-registration follows the real `TestGateRegistration`/`precommit_hook_files_regex` precedent, and the pylint/vulture negative assertions correctly match the Phase 3 precedent (verified: `.pre-commit-config.yaml:27` and `pyproject.toml:87` exclude both `tools/hooks/` and would exclude the new modules).
- The Makefile grep-gate assertions use `tests\.test_config_doctor\b`, which correctly does NOT match `tests.test_config_doctor_pty` (`_` is a word char, so no boundary) — the two counts are genuinely independent.

**Concerns:**
- None new. (The plan remains one of the best-cited in this repo — every line reference I checked resolved.)

**Suggestions:**
- None required.

**Risk Assessment:** **LOW.** All cycle-2 findings fixed with correct repo evidence; the tracer is architecturally sound and its gates are executable.

---

## 04-02

**Summary:** The full 25-row read-only catalog with honest confidence labeling, all cycle-2 findings verifiably fixed — but one new defect in a `<verify>` command that will fail spuriously against a correct implementation.

**Round-2 disposition verification:**
- **MEDIUM — row 6 negative test vs. read spec:** Task 1's `opencode-permissions` read now checks `isinstance(permission, dict)` first and returns `UNKNOWN` immediately for a present-but-non-dict value, explicitly distinct from the absent-key case; the same type-guard is applied to row 16's `modelParameters` in Task 2 with a matching negative test. **RESOLVED** — the test/implementation contradiction is reconciled.
- **LOW — row-20 finding dropped:** `<output>` now instructs the executor to record the open scope question for uz verbatim ("Open question for uz: include rtk's `[tee].max_files` …"), and the Round-2 ledger explicitly corrects Round 1's inaccurate "Deferred: None." **RESOLVED.**

**Strengths:**
- Row arithmetic is internally consistent at every boundary (10 → 24 → 25, matching RESEARCH minus the explicitly-excluded row 20), pinned by acceptance criteria and a row-count check.
- Rows 17/18's unconditional `UNKNOWN`, tested against both empty and fully-populated `cli-config.json`, is exactly the never-silently-pass/fail contract SC-2/SC-3 require.
- The `ReadContext(data, env, runner)` revision is done in the same commit as its first load-bearing consumers, with Wave 1's suite required to pass unmodified — the right additive-change discipline, and Wave 3's `apply_ctx` spec keeps the exact same shape.

**Concerns:**
- **MEDIUM (new) — Task 2's second `<verify>` command fails spuriously against a correct implementation.** The inline row-count check `python3 -c "import importlib.util as u; s=u.spec_from_file_location('cdc','tools/config_doctor_checks.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(len(m.CONFIG_DOCTOR_ROWS))"` execs `config_doctor_checks.py`, which (per 04-01's own spec, and 04-01's own key insight about exactly this hazard) performs a bare module-level `import config_doctor_readers`. From the repo root, `tools/` is not on `sys.path` (`python3 -c` seeds only `''`), so this raises `ModuleNotFoundError` even when the module and its 24 rows are perfectly correct. 04-01 fixed this identical problem inside `load_checks()` with a guarded `sys.path.insert` — 04-02's one-liner omits it. The failure is loud, not silent, but an executor hitting a red gate on a correct build may "fix" it the wrong way (e.g. weakening the module-level import, or adding a `tools/__init__.py` that changes packaging semantics for every existing loader). Fix: prepend `import sys; sys.path.insert(0, 'tools')` inside the `-c` snippet (or count via the test suite's own loader).
- **LOW (nit) — must_haves truth #4's wording ("its section is gated on nothing but `rtk`'s own presence on PATH") contradicts the action and key_links,** which append the cross-runtime section unconditionally whenever any `runtime == "cross"` row exists (rtk-absence is surfaced as a row *value*, `"rtk not installed on PATH"`, not a section gate). The action and the Task 3 tests pin the correct behavior, but an executor reading the truth first could gate the section on `shutil.which("rtk")` and still pass most tests — only the rtk-absent `current_display` assertion would catch it.

**Suggestions:**
- Fix Task 2's `<verify>` one-liner with the `sys.path` insert (one line).
- Reword must_haves truth #4 to "the cross-runtime section is appended unconditionally whenever cross-scoped rows exist; `rtk`'s own presence is a row value, never a section gate."

**Risk Assessment:** **LOW-MEDIUM.** The catalog content and honesty contracts are solid and all cycle-2 findings are genuinely fixed; the broken verify command is a real executor-facing hazard but a one-line fix.

---

## 04-03

**Summary:** The strongest plan of the set on write-path safety, with all four cycle-2 findings verifiably fixed; the one residual prose inaccuracy is a claim cycle 2 already waived.

**Round-2 disposition verification (all RESOLVED):**
- **MEDIUM — JSONC pre-write self-validation:** Task 2's `opencode-share-mode` applier now validates the spliced text in-memory through the reader's own strip+parse path *before* writing, refusing with `{"ok": False, "reason": "refused: spliced JSONC failed self-validation, no write performed"}` and calling no writer on failure; Task 1's `set_jsonc_value` docstring states it performs no self-validation, placing that responsibility on the caller; a fault-injected negative test is specified; T-04-08's mitigation text now names the implementing task. **RESOLVED** — the threat-register/action mismatch is closed.
- **LOW — modal preview naming `apply_row` directly:** Task 3 now says `ctx.apply(row_id, dry=True)` with an explicit "NEVER call `apply_row` directly from this file" note, preserving the no-import seam. **RESOLVED.**
- **LOW — refusal-result UX:** Task 3's behavior and action now specify the modal surfaces the escaped `reason`, does not dismiss or refresh on refusal, and rebinds to an acknowledgement; a unit-level test with an injected refusing `ctx.apply` stub pins it. **RESOLVED.**
- **LOW — `apply_ctx` underspecified:** now `ReadContext(data=None, env=env, runner=None)` with no `paths` field; each applier resolves its own path via `resolve_runtime_config_paths(ctx.env)`; the key_links dispatch description is reconciled (`row.apply` identity, never `row.runtime` inspection). **RESOLVED.**
- Cycle 2's unledgered "post-TOCTOU preview divergence" LOW is now resolved **by construction**: Task 3 specifies the DataTable refresh comes from `ctx.apply`'s own result (not a re-read or the stale evaluated row), which answers "which source wins." Still not ledgered, but no longer an open defect.

**Strengths:**
- The refusal-as-return design is grounded in verified behavior: `tools/wizard_app.py:128-137`'s `WizardCrash` docstring really does document Textual 8.x swallowing unhandled exceptions into graceful shutdown, so the `apply_row` blanket `try/except` + return-dict contract is the correct pattern, and it's pinned at three levels (must_haves, acceptance, action).
- `write_toml_region_replace`'s divergence (swap the statusline-doctor subprocess for `tomllib.loads` + atomic revert, matching the source's revert/no-prior-content branches at `tools/setup.py:493-507`) is the right adaptation.
- The pyright registration is real and asserted: verified `[tool.pyright] include` is a literal list at `pyproject.toml:93`, while the Makefile glob (`Makefile:39`) and pre-commit regex (`.pre-commit-config.yaml:48`) are indeed already generic — pyright was the only genuine gap, and the executed `TestGateRegistration` extension closes it.
- The `<human-check>` block, ONESHOT-RULES Rule 5/6 handling, and the docker/podman `<precondition>` circuit-breaker are exactly right for the one plan that can rewrite real config files.

**Concerns:**
- **LOW (residual, waived by cycle 2) — the "pyright include has no glob support" claim is factually wrong and is still repeated twice** (Task 1's read_first and action). Cycle 2 debunked it and waived action since the prescribed fix (explicit literal append) is correct and safer regardless — but the plan prose still asserts it. Cosmetic; no behavioral impact.
- **LOW — `codex-history-persistence`'s TOML "minimal string-level table/key upsert" is the most underspecified writer of the set.** `set_jsonc_value` enumerates its sub-cases (replace existing / insert first/middle/last / empty object); the TOML upsert does not — e.g. `[history]` exists with `max_bytes` and comments (replace `persistence` in place vs. append vs. create the table). The behavior test ("sets `history.persistence` to `"none"` and every other TOML table/key is unchanged") constrains the outcome, but an executor will face sub-case decisions `set_jsonc_value`'s spec already answered for JSONC. Worth one sentence enumerating the sub-cases, or accepting as an executor decision point.

**Suggestions:**
- Drop or soften the "no glob support" sentence to "kept as an explicit literal list, matching the existing entries" (true and sufficient).
- Enumerate the TOML upsert sub-cases (existing-key-replace / new-key-in-existing-table / create-table) in Task 2's behavior, mirroring `set_jsonc_value`'s case list.

**Risk Assessment:** **LOW-MEDIUM.** All cycle-2 findings genuinely fixed; write-path mechanics remain the phase's strongest work. The two residuals are prose-level.

---

## Cross-Plan Assessment

**Round-2 ledger integrity:** all 9 cycle-2 actionable findings verified genuinely RESOLVED in the plan text with matching repo evidence (per-plan tables above). Both cycle-2 "ledger inaccuracy" complaints (04-02's and 04-03's dropped/unledgered findings) are themselves corrected — 04-02's Round-2 ledger explicitly owns the row-20 drop, and 04-03's Round-2 ledger explicitly owns the unledgered modal-preview finding from cycle 1.

**Dependency ordering:** correct and incremental (tracer → full read-only catalog → apply), each wave leaving prior tests as regression proof; the `ReadContext` and `CheckRow` extensions are additive trailing-defaulted fields, consistent with keyword-argument row construction.

**Goal achievement:** ROADMAP SC-1 through SC-5 are all covered by executed tests rather than prose. The apply-wave's 4-of-25 apply-eligibility is honestly framed in `<source_audit>` as tracer-first discipline with a data-change extension path, which matches D-01's premise and REQUIREMENTS.md's actual contract (which mandates informational rows *never* get apply, not that all eligible rows get one this phase).

**Findings this cycle:** 0 HIGH, 1 MEDIUM (04-02 Task 2's spurious-failure `<verify>` one-liner — the only finding that would actually block or mislead an executor), 3 LOW (04-02 truth-#4 wording, 04-03's repeated debunked pyright-glob claim, 04-03's underspecified TOML upsert sub-cases).

**Overall risk: LOW-MEDIUM.** The cycle-2 convergence genuinely landed — this is likely the final cycle. One one-line verify-command fix (plus optional wording cleanups) and the plan set is ready for execution.

---

## Consensus Summary

Single-reviewer cycle (opencode only; the `claude` lane was skipped for independence since this review was run from inside Claude Code, and gemini/codex/cursor/antigravity were available but not selected — only `--opencode` was requested per the invocation). All findings below carry only one reviewer's weight; no cross-reviewer corroboration was possible this cycle.

### Agreed Strengths
N/A — single reviewer this cycle.

### Agreed Concerns
N/A — single reviewer this cycle. See per-plan sections above for the full, source-grounded findings list.

### Divergent Views
N/A — single reviewer this cycle.
