## Review: docs/superpowers/plans/2026-10-10-system-one-provisioning.md; docs/superpowers/plans/2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### CRITICAL
- **Invalid GPU selection persists System One as enabled** — Location: provisioning Task 6, lines 849–888. Required: Any KFD, vendor, or render-node failure leaves `system_one.enabled: false`; persist `true` only after all checks pass. Why: the implementation writes `true` before vendor/render validation, contradicting its own non-ROCm test.
- **Mandatory Python verification gates are omitted** — Location: provisioning Global Constraints lines 37–38; Tasks 1, 3, 6, and 8. Required: Every task editing `.py` runs `make validate && make test` before commit. Why: targeted pytest commands—and no verification in Task 8—violate both the plan and `AGENTS.md`.
- **Live VRAM gate is both forbidden and nonfunctional** — Location: provisioning Task 11, lines 1348–1372. Required: Implement the check as an `llmenv.py` subcommand and pass PID/reserve arguments correctly. Why: `uv run python3` violates the CLI-only Python rule, and arguments placed after the heredoc become shell commands rather than `sys.argv`.
- **Explicit-backend probe contract contradicts its implementation** — Location: decision-skill Review Focus line 47; Task 2 lines 125–126, 236–242, 338–347. Required: `--probe` returns `status: unavailable` and `reason: backend_unavailable:typesafe:missing_api_key`, with a test asserting it. Why: the declared output contains no `status` or composite `reason`.
- **Evaluation bypasses the kill switch** — Location: decision-skill Global Constraints lines 31–32; Task 5 lines 633–656. Required: `eval_cases.py` sends nothing unless `GSD_PATH_JEV=1`, with a no-request test for the unset case. Why: direct `dispatch()`/`checked_response()` calls bypass `screen()` and its guard.

### HIGH
- **Setup block nesting is internally inconsistent** — Location: provisioning Task 6, lines 866–919. Required: Provide one exact block layout placing GPU validation and prefetch inside the combined gate and llm-server Steps 3–7 inside their narrower gate. Why: the shown `fi` closes the combined block before the later-stated prefetch insertion point.
- **Idle-CPU task is not executable as a plan** — Location: provisioning Task 8, lines 1087–1127. Required: Identify the measured fix and provide its exact environment/code change and assertion before implementation begins. Why: `<VAR>/<VALUE>` and “first candidate that works” leave a material design decision unresolved.
- **System One check-setup cannot detect its intended failures** — Location: provisioning Task 9, lines 1196–1230. Required: Execute the `jq` predicate inside `record_command`, use the established failure counter, and compare the pinned compose node with detection. Why: the external pipe checks diagnostic output instead of command output, `bad` is undefined in `check-setup.sh`, and the mismatch test has no implemented comparison.
- **System One check fixtures omit required GPU facts** — Location: provisioning Task 9, lines 1148–1171. Required: Extend `run_check_setup_with_stubs` with AMD vendor data and isolated render-node paths. Why: its current detect fixture has no `vendor`, while the planned predicate requires `0x1002`.
- **Choice evaluation has no correctness rule** — Location: decision-skill Task 5, lines 633–656. Required: Define and test scoring for choice and shorthand cases. Why: the case set must include them, but implementation specifies correctness only for noul and score.
- **Backend result files are written before they exist** — Location: decision-skill Tasks 5–6, lines 655–679. Required: Create `backends/*.md` before Task 5 records results, or defer recording until Task 6. Why: the authoritative skill currently has no `backends/` directory.
- **Calibration has no implementable interface** — Location: decision-skill Task 7, lines 689–695. Required: Define a calibration function/CLI, its case-level inputs, deterministic threshold ordering, and tests including the `None` result. Why: Task 5 exposes only aggregate reporting, while Task 7 requires testing an undefined calibration operation.
- **Receipt hash semantics drift from the existing contract** — Location: decision-skill Task 3 line 463; Task 6 line 680. Required: Choose and consistently test/document whether `request_sha256` hashes the input payload or exact wire request. Why: the plan changes it to payload-only while `reference.md` promises the exact canonical request sent.
- **Reference batching guidance remains false for Laya** — Location: decision-skill Task 6 line 680; existing `reference.md` lines 21–38. Required: Replace shared-state batching language with backend-specific semantics. Why: Task 6 moves service details but does not require correcting the retained claim that all items share one request/state.

### MEDIUM
- **Setup tests depend on the host’s real `/dev/dri`** — Location: provisioning Task 6, lines 680–766, 874–888. Required: Inject a configurable DRI root and create fake render nodes in fixtures. Why: fake detection returns `renderD129`, but production code checks the real host path.
- **Skill-judge acceptance leaves D1 undefined** — Location: decision-skill Task 8, lines 700–706. Required: State an explicit D1 floor out of 20. Why: “12/15, or 8/10 for D7” does not cover D1’s 20-point scale.

### Cross-Document Consistency
- **Task 7 is incorrectly classified as Laya-independent** — Location: both execution-order headers, line 5; decision-skill Task 7 lines 689–695. Required: Schedule Task 7 after the live Task 5 evaluation and provisioning dependency, or calibrate solely from committed fixtures. Why: both plans say Task 7 can run without Laya, but it explicitly consumes Task 5 live results.

### Status: Issues Found — fix and re-invoke
