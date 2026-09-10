I need to verify plan claims against the actual repo. Let me read the key referenced files.
Let me grab exact line numbers in the plan files for the key disposition evidence.
# Cross-AI Plan Review — Phase 4 (Config Doctor), Cycle 2

Verification method: I checked every load-bearing citation and mechanism claim against the live repo — `tools/setup.py` (`stdin_on_tty` 926-945, `_read_json_checked` 1363-1380, `_atomic_write_json` 1383-1424 incl. the port-not-import docstring at 1386-1388, `read_toml` 191-200, `write_toml_preserving` 451-508, `launch_wizard` 2447-2524 with the `stdin_on_tty` wrap at 2503-2504, `main` argparse 2717-2749, `cmd_doctor`/`cmd_check` 2603-2617), `tools/wizard_app.py` (palette 27-36, `WizardContext.commit: object = None` at 121, `WizardCrash` Textual-swallow docstring 128-137, `run_wizard` 940), `tools/hooks/detect.py` (`_probe_rtk_hook` 73-96), `skills/ai-kit-opencode-providers/.../jsonc_edit.py` (`find_provider_object` 155-186, `significant_indices`/`strip_jsonc_comments`/`code_indices`/`strip_trailing_commas` 251-320), `03-RESEARCH.md:528-540` (verbatim rtk output block), `tests/test_wizard_pty.py` (helpers 52-205, `spawn_pty_piped_stdin` 100-134), `tests/test_tool_substitution_hook.py` (`fake_bin` 58, `scoped_env` 69, `precommit_hook_files_regex` 80, `TestGateRegistration` 964), `Makefile:33-55`, `.pre-commit-config.yaml:21-64`, `pyproject.toml:87-95`, and `tools/hooks/README.md`'s closing fold-in line. Nearly every citation is accurate. All three Round-1 ledger dispositions per plan check out; findings below are the residual and new issues.

## 04-01

**Summary:** A well-grounded tracer plan that proves the full four-layer architecture (presence probe → 3-state readers → D-01 declarative engine → textual TUI via `--config-doctor`) on one real row. All three cycle-1 findings are genuinely fixed in the plan text with the correct repo precedents cited.

**Strengths:**
- `read_toml_checked`-is-new is correct and correctly justified: `tools/setup.py:192`'s own docstring ("Missing / empty / malformed → {}") documents exactly the conflation Phase 3 fixed for JSON (`tools/setup.py:1364-1370`); reusing it would reintroduce Pitfall 3's bug for Codex.
- The `stdin_on_tty()` fix is complete and verifiable: wrap specified in Task 1 action (04-01-PLAN.md:452), pinned by must_haves truth #8 (line 36), an acceptance criterion, and a `<verify>` grep; the piped-stdin PTY test replicates the real harness (`spawn_pty_piped_stdin`, verified at `tests/test_wizard_pty.py:100-134`) — and the plan correctly explains why a plain PTY test cannot catch the omission.
- `reads_section_file` is defined now with the degrade-logic branch (04-01-PLAN.md:301-360) rather than patched in Wave 2 — internally consistent from the first commit, with the honest caveat that Wave 1 never exercises `False`.
- Loader fix is correct: `load_checks()` seeds `tools/` on `sys.path` and loads readers first (04-01-PLAN.md:466-475), mirroring the verified pattern at `tests/test_ai_kit_opencode_providers.py:13-17`.
- Gate-registration by executed assertion follows the real precedent (`TestGateRegistration` at `tests/test_tool_substitution_hook.py:964`, `precommit_hook_files_regex` at line 80) — needed because pre-commit silently skips unmatched files (`py-compile` `files:` at `.pre-commit-config.yaml:48`).
- Registering the PTY suite under the system-python3 `unittest (core)` hook is safe: `tests/test_wizard_pty.py` imports only stdlib (verified lines 20-32); textual resolves in the child via `uv run --script` (PEP-723 header at `tools/setup.py:2-8`).

**Concerns:**
- **MEDIUM — Cursor path resolution omits the documented XDG fallback, contradicting the plan's own research.** Task 1 (04-01-PLAN.md:319, read_first at 233) resolves cursor as `CURSOR_CONFIG_DIR > ~/.cursor/cli-config.json`, explicitly mirroring `tools/setup.py:57-58` — which is *ai-kit's installer* precedence for `hooks.json`, not Cursor CLI's documented *config* precedence. `04-RESEARCH.md` Pattern 2 states Cursor's documented override is `CURSOR_CONFIG_DIR` falling back to `$XDG_CONFIG_HOME/cursor/cli-config.json` on Linux/BSD, *then* `~/.cursor/cli-config.json` (cited to cursor.com/docs/cli/reference/configuration, and flagged "not yet implemented anywhere in this repo"). On an XDG-layout machine, Config Doctor will silently skip a present Cursor config — the exact "section skipped rather than shown" miss D-03 exists to prevent. The plan's own framing ("porting the precedence each runtime's own tooling already establishes") is violated for this one runtime. opencode/Codex/Claude resolutions are all correct.
- **LOW — `read_jsonc_checked`'s port list is incomplete.** Task 1 read_first names `_classify`/`strip_jsonc_comments`/`strip_trailing_commas`, but `strip_trailing_commas` depends on `code_indices` (`jsonc_edit.py:285-299`), which neither 04-01 nor 04-03 ever names (grep-verified: zero mentions). An executor porting "these two helpers verbatim" hits a NameError and must improvise; name the third dependency.
- **LOW — pylint, not just ruff E402, will flag the function-scoped imports.** `tools/setup.py` *is* inside the pylint hook's `files:` regex (`.pre-commit-config.yaml:27`), and `launch_wizard`'s own `import wizard_app` carries `# pylint: disable=import-outside-toplevel` (`tools/setup.py:2482`). The plan's new in-body imports in `cmd_config_doctor` will trip the same warning in `make validate`; the plan cites only the E402 reason. Trivial fix, but unstated.
- **LOW — cycle-1's "no dead apply affordance in Wave 1" suggestion was never incorporated**, and the ledger's "Deferred: None" doesn't mention it. Resolved by construction (Wave 1's `BINDINGS` specify only `"q"`, and 04-03 Task 3 gates `"a"` on `apply_eligible` + `ctx.apply is not None`), but the plan never pins it explicitly.

**Suggestions:**
- Add the `$XDG_CONFIG_HOME/cursor` intermediate to cursor's resolution (or explicitly document why it's deliberately omitted, per D-03's live-verified `~/.cursor/cli-config.json`), and add a presence test for the XDG case.
- Add `code_indices` to the port list in Task 1's read_first.
- Note the `# pylint: disable=import-outside-toplevel` need for `cmd_config_doctor`'s in-body imports.

**Risk Assessment:** **LOW-MEDIUM.** Architecture, citations, and the three cycle-1 fixes are all verified solid; the Cursor XDG-precedence gap is the only correctness defect, and it's a cheap fix.

**Disposition Verification (Round 1 — 8982557):**
| Finding | Verdict | Evidence |
|---|---|---|
| HIGH — missing `stdin_on_tty()` wrap | **RESOLVED** | Wrap specified verbatim-mirroring `tools/setup.py:2503-2504` (04-01-PLAN.md:452), pinned by truth #8 (line 36), acceptance criterion, `<verify>` grep, notes item 6, plus the piped-stdin PTY test using the verified `spawn_pty_piped_stdin` harness. The claim that a PTY alone can't catch it is technically sound (a PTY always supplies fd 0). |
| MEDIUM — test loader `ModuleNotFoundError` | **RESOLVED** | `load_checks()` inserts `tools/` on `sys.path` + `load_readers()`-first (04-01-PLAN.md:466-475); acceptance criterion present; mirrors the real pattern at `tests/test_ai_kit_opencode_providers.py:13-17`. |
| MEDIUM — unreadable-file short-circuit vs. non-section-file rows | **RESOLVED** (root design) | `CheckRow.reads_section_file: bool = True` field + conditional short-circuit in `evaluate_row` (04-01-PLAN.md:301-360), acceptance criteria, notes item 5; consumers + regression tests verified present in 04-02 (lines 202, 286, 440, 506). |
| LOW — dead apply affordance in Wave 1 | **RESOLVED (implicitly, not ledgered)** | No `"a"` binding exists in Wave 1's spec; 04-03 Task 3 gates the binding on eligibility. Never explicitly stated, and the ledger omits it entirely — a ledger-completeness nit, not a defect. |

## 04-02

**Summary:** Expands the catalog to all 25 RESEARCH rows with honest confidence labeling, unconditional-`unknown` rows for the genuinely unresolved Cursor settings, and a correctly-executed `ReadContext` revision with regression proof. All three ledgered cycle-1 findings are genuinely fixed. One new internal contradiction (row 6's negative test vs. its read spec) and one dropped cycle-1 finding (the row-20 checkpoint).

**Strengths:**
- The row-12 matcher fix is complete and self-verifying: lowercase `"hook"` (04-02-PLAN.md:590-592), docstring citing `03-RESEARCH.md:527-540`, and a test fixture built from the *verbatim* verified block including the `[ok] Hook: rtk hook claude` decoy (verified real at `03-RESEARCH.md:533` and `:539`) — the stub can no longer drift from reality. I verified the existing `_probe_rtk_hook` matcher at `tools/hooks/detect.py:88` is capital-`Hook`-only, so a naive copy would indeed never have matched the Cursor line; the plan's reasoning is sound.
- `claude-telemetry`'s and `cursor-sandbox-json`'s `reads_section_file=False` dispositions include the exact regression tests cycle 1 asked for (malformed section file + knowable alternate source → real value, while sibling rows degrade) — 04-02-PLAN.md:286-290 and 506-512.
- `claude-telemetry`'s `why` scopes the claim to process env only (04-02-PLAN.md:311 and ledger line 841), resolving the settings-`env`-block ambiguity honestly rather than inventing an undocumented precedence.
- Permanently-informational rows (5, 9, 16, 17, 18) distinguished in their own `why` text from "not yet wired" — the honesty contract SC-3 requires. Row 7b's honest LOW confidence for the `router-env` custom router (Assumption A2) is exactly right.
- Row arithmetic is internally consistent: 1 + 5 + 4 + 6 + 8 + 1 = 25, matching RESEARCH minus the explicitly-excluded row 20, with acceptance criteria pinning 10/24/25 at each task boundary.

**Concerns:**
- **MEDIUM — row 6's negative test contradicts its own read spec (executor-blocking).** The read function builds its summary via `get_nested(ctx.data, "permission", <action>, default=<documented default>)` (04-02-PLAN.md:242-244); when `"permission"` is a JSON *string*, `get_nested` returns each action's documented default (its documented behavior: "returning `default` the moment any intermediate value is missing or not a dict"), so every entry "differs" from nothing and the summary is `"all defaults (see Why...)"`. But the negative test (04-02-PLAN.md:283) asserts `current_display` degrades to `"unknown"`. As specified, that test fails against that implementation. The fix is a one-line `isinstance(permission, dict)` check returning `UNKNOWN` before the loop — specify it. (Must_haves truth #6's "`modelParameters` entry whose value is not a list" example is similarly loose vs. the repr-based reader for row 16.)
- **LOW — cycle-1's row-20 checkpoint finding was dropped, not resolved.** Cycle 1 (04-REVIEWS.md:66) said the exclusion deserves an explicit `checkpoint:human-verify`-style flag because the *user's own stated intent* (CONTEXT.md open question 7) proposed the ~100 value. The revision documents the exclusion reasoning well in `<source_audit>` but adds no checkpoint, no question to uz in `<output>`, and the ledger's "Review Feedback Deferred: None" (line 845) is inaccurate — a raised finding simply vanished. Per this repo's own workflow rules, a scope question with a user-stated preference should surface as a checkpoint, not be closed in an audit table.

**Suggestions:**
- Specify row 6's reader to check `isinstance(permission, dict)` first and return `UNKNOWN` otherwise, reconciling the test; do the same explicit type-guard for row 16's `modelParameters`.
- Add the row-20 scope question to 04-02's `<output>` (or a `checkpoint:human-verify` in 04-03's close-out) so uz actually sees it, and correct the "Deferred: None" row.

**Risk Assessment:** **LOW-MEDIUM.** Catalog content and honesty contracts are excellent and the cycle-1 HIGH is genuinely dead; the row-6 contradiction will surface as an executor decision point mid-task but has an obvious one-line fix.

**Disposition Verification (Round 1 — 8982557):**
| Finding | Verdict | Evidence |
|---|---|---|
| HIGH — matcher requires capital `"Hook"`, can never match real output | **RESOLVED** | Matcher now `"Cursor"` + lowercase `"hook"` (04-02-PLAN.md:590-592); docstring + test fixture cite `03-RESEARCH.md:527-540` verbatim including the Claude decoy line (ledger line 839; verified the block at `03-RESEARCH.md:533/539`). I independently verified the decoy line does not contain "Cursor" and the Cursor line does not contain capital-"Hook"-only tokens, so the matcher is correct against the verified output. |
| MEDIUM — unreadable short-circuit vs. `claude-telemetry`/`cursor-sandbox-json` | **RESOLVED** | `reads_section_file=False` on both rows (04-02-PLAN.md:202, 440) + regression tests against malformed section files (286-290, 506-512); ledger line 840. |
| LOW — telemetry reads only process env | **RESOLVED** | `why` text explicitly scopes to process-environment value only (04-02-PLAN.md:311, ledger line 841, notes item 5 at line 780). |
| LOW — row-20 exclusion should be a user checkpoint | **NOT RESOLVED** | No checkpoint, no question in `<output>`, absent from both ledger tables while "Deferred" claims "None" (line 845). Exclusion reasoning itself is documented and defensible; the *process* finding stands. |

## 04-03

**Summary:** The strongest plan of the three on write-path safety: ported-never-imported writers with executed failure-injection byte-identity tests, a categorical `cleanupPeriodDays: 0` refusal, per-item confirm with literal-resulting-config, a no-bulk-apply tripwire with honest framing, and a real end-to-end PTY apply test. All three ledgered cycle-1 findings are genuinely fixed. One new gap: the JSONC apply path lacks the pre-write self-validation its own threat register claims.

**Strengths:**
- The pyright fix is real and asserted: Task 1 edits `[tool.pyright] include` (a genuine gap — verified at `pyproject.toml:93` it's a literal list) and extends `TestGateRegistration` with an executed assertion (04-03-PLAN.md:267-276, 296), so the four-file set stays pinned as it grows.
- The refusal-as-return fix is complete: `_apply_claude_retention` returns `{"ok": False, "reason": "refused: cleanupPeriodDays 0 is never writable"}` and never raises (04-03-PLAN.md:363), `apply_row` wraps every applier call in `try/except Exception` (line 412), and the rationale is grounded in the verified Textual-swallow behavior (`tools/wizard_app.py:128-137`). The guard's independence from `apply_target` (Pitfall 2) is preserved.
- The tripwire fix is complete: pattern extended with `rows`/`selected`/`each` (04-03-PLAN.md:551, ledger line 713-715), must_haves softened to name `apply_row`'s one-`row_id` signature as the primary architectural guarantee (line 28), and the test's own docstring must state it's a naming tripwire, not exhaustive proof.
- `write_toml_region_replace`'s divergence from `write_toml_preserving` (swap the statusline-doctor subprocess for `tomllib.loads` + revert) is the right adaptation — I verified the source's revert/no-prior-content branches at `tools/setup.py:493-507` match what the plan ports.
- `_atomic_write_json`'s port spec matches the real source exactly (mode 0o600-fresh/copy-existing, fsync, unlink-then-re-raise — verified at `tools/setup.py:1383-1424`), and the failure-injection byte-identity tests follow the established Phase 3 discipline.
- The `<human-check>` block and ONESHOT-RULES Rule 5/6 handling for the one plan that can rewrite real config files is exactly right; `make e2e-docker` and its failure string are real (`Makefile:50-55`).

**Concerns:**
- **MEDIUM — the JSONC apply path has no pre-write self-validation, contradicting its own threat register.** T-04-08 claims "`set_jsonc_value`/`write_toml_region_replace` self-validate the new content before committing (JSONC via the same strip+parse path the reader uses)" — but no task specifies it. Task 1's `<behavior>` for `set_jsonc_value` covers splice correctness only (04-03-PLAN.md:176-178); Task 2's `opencode-share-mode` applier reads text → `set_jsonc_value` → `_atomic_write_text` with no validation and no revert (line 385). The TOML writer gets `tomllib.loads` + revert; the JSON writer can't fail (dict serialization); the JSONC text splicer — the *one* writer whose new replace/insert operations are untested machinery ported from delete-only code (`remove_provider`) — gets nothing. A span-detection bug writes atomically-corrupt JSONC to `opencode.jsonc`, the exact core-value violation this project exists to prevent. Specify: validate the spliced text via the reader's strip+parse path before writing; on failure, refuse without writing.
- **LOW — the modal-preview seam wording still names `apply_row` directly.** Task 3 says the modal renders "`apply_row(row_id, dry=True)`'s `literal_resulting_config` text" (04-03-PLAN.md:525) — but `config_doctor_app.py` must import nothing from `config_doctor_checks.py`, so the preview must go through `ctx.apply(row_id, dry=True)`. This cycle-1 LOW (04-REVIEWS.md:91) was not ledgered and not fixed; an executor reading literally could add a forbidden import. The behavior section's `ctx.apply(row_id, dry=False)` (line ~560) makes the natural implementation correct, but the prose should name the seam path.
- **LOW — refusal-result UX unspecified.** Behavior covers confirm→write→refresh and cancel, but not `ok: False`: nothing requires surfacing the refusal `reason` to the user, and the table-refresh-on-refusal is unspecified. A refused apply that silently dismisses the modal would violate the project's never-silently-fail rule.
- **LOW — `apply_ctx` is underspecified.** Task 2 calls it "a `config_doctor_checks.ReadContext`-shaped object carrying the resolved per-runtime paths" — but `ReadContext` has fields `(data, env, runner)` and no paths field. Appliers can (and should) derive paths from `ctx.env` via `resolve_runtime_config_paths(env)`, which is deterministic; say so, or specify the field extension. Relatedly, key_links says `apply_row` "inspects `row.runtime` to pick the right format-specific applier" while the action specifies per-row `apply` functions calling writers directly — both work, but pick one description.
- **NIT — "[tool.pyright] include has no glob support" is factually wrong** (pyright supports glob patterns in `include`), but the literal-list fix is correct and safer regardless; also `include` currently holds a *directory* entry (`tools/hooks`, `pyproject.toml:93`), so a glob/directory entry would have been an alternative. No action needed beyond not repeating the claim.

**Suggestions:**
- Add the JSONC pre-write validation + refuse-on-invalid to Task 1's `<behavior>` and Task 2's applier spec, closing the T-04-08/action mismatch.
- Reword the modal preview as `ctx.apply(row_id, dry=True)`; specify refusal-result rendering (show `reason`, leave the row unchanged).
- Specify how appliers resolve their target file from `ctx.env`.

**Risk Assessment:** **MEDIUM.** The write-path mechanics are thorough and repo-grounded, and all three ledgered fixes verified; the unvalidated JSONC write is the one real residual risk on the plan that mutates real config files — cheap to specify now, expensive to discover later.

**Disposition Verification (Round 1 — 8982557):**
| Finding | Verdict | Evidence |
|---|---|---|
| MEDIUM — `config_doctor_appliers.py` never registered in `[tool.pyright] include` | **RESOLVED** | Task 1 appends the path (04-03-PLAN.md:267) + `TestGateRegistration` extension with executed assertion (276, 296) + acceptance criterion; verified `[tool.pyright] include` is a literal list at `pyproject.toml:93` and that the Makefile/pre-commit gates are indeed already generic (`Makefile:39` glob, `.pre-commit-config.yaml:48` regex), so pyright was the only real gap. |
| MEDIUM — refusal via `raise ValueError` is a Textual crash path | **RESOLVED** | Return-dict refusal (04-03-PLAN.md:363) + `apply_row`'s blanket `try/except` (line 412) + acceptance criteria + notes item 4; Textual-swallow behavior verified documented at `tools/wizard_app.py:128-137`. |
| LOW — tripwire misses plural/selector names; must_haves overclaims | **RESOLVED** | Pattern extended (line 551), must_haves reframed as tripwire with the architectural guarantee primary (line 28), test docstring must state the limitation; ledger line 713-715. |
| LOW — modal preview should go through `ctx.apply`, not a direct `apply_row` reference | **NOT RESOLVED** | Line 525 still says "`apply_row(row_id, dry=True)`'s ... text"; not ledgered; "Deferred: None" inaccurate. |
| LOW — which source wins if preview and evaluated row diverge post-TOCTOU | **NOT RESOLVED** | Unaddressed and unledgered. Minor, but the "Deferred: None" row is again inaccurate. |

## Cross-Plan Assessment

**Dependency ordering:** correct and genuinely incremental (tracer → full read-only catalog → apply), each wave leaving the prior wave's tests as regression proof, and Wave 3's `CheckRow` extension designed as additive trailing-defaulted fields — consistent with how Waves 1-2 construct rows by keyword. The `ReadContext` revision in 04-02 Task 1 is done in the same commit as its first load-bearing consumer with Wave 1's suite required to pass unmodified — the right discipline.

**Goal achievement:** ROADMAP SC-1–SC-5 are all covered by executed tests, not prose. Row 20's exclusion is documented and defensible against REQUIREMENTS.md's literal wording, but per cycle 1 (and still unresolved) it should surface to uz as an explicit question rather than being closed in an audit table.

**Ledger integrity (cycle-2-specific):** all 9 ledgered dispositions verified RESOLVED with plan-text and repo evidence. However, both 04-02 and 04-03 declare "Review Feedback Deferred: None" while each silently dropped one and two raised LOW findings respectively — the dispositions ledgers are incomplete, which matters for a process that treats these tables as the audit trail.

**Top fixes before execution (ranked):**
1. **04-02:** reconcile row 6's negative test with its read spec (isinstance guard → `UNKNOWN`) — as written the test fails against the specified implementation.
2. **04-03:** specify pre-write JSONC validation (strip+parse, refuse-on-invalid) to make T-04-08's claimed mitigation real.
3. **04-01:** add Cursor's documented `$XDG_CONFIG_HOME/cursor` fallback (or document its deliberate omission) — the current resolver ports ai-kit's hooks precedence instead of Cursor CLI's config precedence, contradicting the plan's own research.
4. **04-02/04-03:** surface the row-20 scope question to uz (checkpoint or output question), and correct the two "Deferred: None" ledgers.

**Overall risk: MEDIUM** — unusually well-researched, well-cited plans whose cycle-1 defects are genuinely fixed; the residual items are one internal test/spec contradiction, one unvalidated write path on the plan that mutates real config files, and one path-resolution gap versus cited documentation. All are small, plan-level fixes that should land before dispatching executors.
