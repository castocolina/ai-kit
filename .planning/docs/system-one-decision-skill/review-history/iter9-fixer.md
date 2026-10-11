## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Runtime dependency is undeclared / Undeclared `sd` runtime dependency in a validation gate** — Severity: HIGH. Status: addressed. Edit: `system_one_render_matches` now takes the first `/dev/dri/` device from `yq` and extracts the node with `${raw#*/dev/dri/}` and `${pinned%%:*}`. Section: Task 9 Step 3.
- **GPU vendor detection lacks a direct test** — Severity: MEDIUM. Status: addressed. Edit: Task 6 adds `test_list_gpus_reads_device_vendor_and_missing_vendor_file` in `tests/test_detect.py` (card1 `0x1002`, card0 missing file yields `""`) and includes that file in the failing-test command and the commit. Section: Task 6 Steps 1–2 and 5.
- **18.2 GB research image orphaned** — Severity: MEDIUM. Status: addressed. Edit: Task 11 Step 1 removes the research container `laya`, the image `localhost/laya-rocm`, and the volume `laya-cache` before Step 2 builds `localhost/llm-env-system-one:rocm`. Section: Task 11 Step 1.

### Findings escalated
- None.

### Findings skipped (with disagreement noted)
- **OmniRoute wait inherits the System One timeout** — Severity: MEDIUM. Reason: owner rejected the premise. A variable assignment prefixed to a bash function call does not persist after the call, so `start.sh`'s `LLM_ENV_HEALTH_TIMEOUT_SECONDS=… wait_for_health` is left unchanged. NOT addressed in this pass.

### Findings not yet addressed
- None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **Live evaluation can silently calibrate from incomplete data** — Severity: HIGH. Status: addressed. Edit: `eval_cases.py` exits 1 on any non-ok case and when `n != 32`, before printing metrics or writing `notes/eval-results.json`; Task 8 check 6 treats that as a failure and does not calibrate from it. Section: Task 5 `main()` and Step 4; Task 8 check 6.
- **Log-count gates are timestamp-racy** — Severity: MEDIUM. Status: addressed. Edit: LIVE checks 2, 5, 7, and 9 count `POST /v1/systemone` as the delta of `podman logs` line counts immediately before and after the batch, via `posts()`. Section: Task 8 Step 2.
- **LIVE check 3 rests on an unstated determinism assumption** — Severity: MEDIUM. Status: addressed. Edit: Task 5 sends the alone vague item twice and stores `repeat_max_prob_diff`; LIVE 3 tolerance is `max(1e-3, 2 × that value)`. `--record` keeps that sibling key; `--calibrate` ignores it. Section: Task 5 Step 4; Task 8 check 3.
- **FIX-lane model id is the only one never verified** — Severity: MEDIUM. Status: addressed. Edit: Round 1 verifies `opencode-go/glm-5.3`, `gemini-3.1-pro`, and `grok-4.7-high-fast`. The glm lane is `opencode run --auto -m opencode-go/glm-5.3` and its prompts say to read files larger than 50 KB in chunks. Gemini stays `cursor-agent` `gemini-3.1-pro`. Section: Task 8 intro and Step 3.
- **Kill-switch return moved after the stdin read** — Severity: MEDIUM. Status: addressed. Edit: `screen()` returns `{"status":"disabled"}` when `GSD_PATH_JEV != "1"` before `json.load(sys.stdin)`. Section: Global Constraints; Task 3 Step 3.

### Findings escalated
- None.

### Findings skipped (with disagreement noted)
- None.

### Findings not yet addressed
- None.

### Status: Edits Applied

Skipped a live log-format check and did not run either plan. Risk: `opencode run`'s default stdout may add a trailer after `VERDICT`, so `lane_ok` can fail even when the model’s last sentence is the verdict.
