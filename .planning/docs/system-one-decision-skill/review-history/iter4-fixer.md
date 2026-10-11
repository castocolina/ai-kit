## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Invalid GPU selection persists System One as enabled** — Severity: CRITICAL. Status: addressed. Edit: `system_one.enabled: true` is written only after the KFD, vendor, and render-node checks pass; each failure writes `false` and then dies, and the refuse tests assert `"false"`. Section: Task 6 Step 3.
- **Mandatory Python verification gates are omitted** — Severity: CRITICAL. Status: addressed. Edit: Global Constraints state the pre-commit gate, and every task that edits a `.py` file (Tasks 1–10, including 2 and 7) runs `make validate && make test` before commit. Section: Global Constraints; Tasks 1, 2, 3, 6, 7, 8.
- **Live VRAM gate is both forbidden and nonfunctional** — Severity: CRITICAL. Status: addressed. Edit: Task 11 records `vram_used_mib` from `uv run llmenv.py detect` with System One stopped, starts it, sends one decision request, and asserts the delta with shell arithmetic. Section: Task 11.
- **Setup block nesting is internally inconsistent** — Severity: HIGH. Status: addressed. Edit: One `if` places GPU validation and prefetch inside the combined gate and Steps 3–7 inside the llm-server gate, with the two existing bodies marked `REPLACE THIS LINE`. Section: Task 6 Step 3.
- **Idle-CPU task is not executable as a plan** — Severity: HIGH. Status: addressed. Edit: Task 8 is an explicit bounded investigation: measurement commands, a five-row env table, idle < 5 and latency ≤ 20 ms, a test that pins the winning row, and stop-and-report if none qualifies. Section: Task 8.
- **System One check-setup cannot detect its intended failures** — Severity: HIGH. Status: addressed. Edit: The vendor `jq` and the compose-node comparison run as `record_command` commands so a mismatch increments `FAIL`; `bad` is gone. Section: Task 9 Step 3.
- **System One check fixtures omit required GPU facts** — Severity: HIGH. Status: addressed. Edit: `run_check_setup_with_stubs` gains `vendor: 0x1002`, a fake KFD file, an isolated DRI tree, and a compose file pinned to `renderD128`. Section: Task 9 Step 1.
- **Setup tests depend on the host’s real `/dev/dri`** — Severity: MEDIUM. Status: addressed. Edit: Setup reads `LLM_ENV_DRI_PATH` (default `/dev/dri`); `run_setup_no_gpu` always creates `tmp_path/dri/renderD129`. Section: Task 6 Steps 1 and 3.
- **Task 7 is incorrectly classified as Laya-independent** — Severity: cross-document. Status: addressed. Edit: The execution-order header puts decision-skill Task 7 with the live Laya steps and lists Tasks 0–4, 6, and 8 as the tasks that do not need Laya. Section: execution-order header.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **Explicit-backend probe contract contradicts its implementation** — Severity: CRITICAL. Status: addressed. Edit: `--probe` prints `status: unavailable` and `reason: backend_unavailable:typesafe:missing_api_key`, and the Task 2 test asserts both. Section: Review Focus item 3; Task 2.
- **Evaluation bypasses the kill switch** — Severity: CRITICAL. Status: addressed. Edit: `eval_cases.py` scores only through `screen()`, and a test asserts `LayaStub.bodies` stays empty when `GSD_PATH_JEV` is unset. Section: Global Constraints; Task 5.
- **Choice evaluation has no correctness rule** — Severity: HIGH. Status: addressed. Edit: `case_correct` treats choice and shorthand as `answer["choice"] == expected`, with a unit test for both plus noul and score. Section: Task 5.
- **Backend result files are written before they exist** — Severity: HIGH. Status: addressed. Edit: Task 5 writes `notes/eval-results.json`; Task 6 creates `backends/*.md` and copies that report in. Section: Tasks 5 and 6.
- **Calibration has no implementable interface** — Severity: HIGH. Status: addressed. Edit: `calibrate(cases) -> float | None` takes `{top, correct}` rows, orders thresholds by `(T, fallback_rate)`, and is tested for `None` and for `0.50`. Section: Task 7.
- **Receipt hash semantics drift from the existing contract** — Severity: HIGH. Status: addressed. Edit: `request_sha256` is the sha256 of the exact `send()` wire bodies, concatenated in item order, with `test_request_sha256_is_the_wire_bodies` and the same sentence in the `reference.md` edit. Section: Task 3; Task 6 `reference.md` bullet.
- **Reference batching guidance remains false for Laya** — Severity: HIGH. Status: addressed. Edit: Task 6 replaces the shared-state paragraphs with per-backend batching: one request for TypeSafe and OpenCode, one request per item for Laya. Section: Task 6.
- **Skill-judge acceptance leaves D1 undefined** — Severity: MEDIUM. Status: addressed. Edit: Acceptance is total ≥ 96/120; any dimension under 80% of its skill-judge maximum gets that dimension’s listed improvement, then a re-judge. Section: Task 8.
- **Task 7 is incorrectly classified as Laya-independent** — Severity: cross-document. Status: addressed. Edit: The header runs Task 7 after Task 5’s live eval; Task 7 reads `notes/eval-results.json` and does not re-call Laya. Section: execution-order header; Task 7.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Did not run the plan’s tests or start a GPU container; Laya 0.4.2 was read from the image only. Risk: the two `true # REPLACE THIS LINE` markers in the setup layout must be replaced with today’s Step 2 and Steps 3–7 bodies, or llm-server setup is dropped.
