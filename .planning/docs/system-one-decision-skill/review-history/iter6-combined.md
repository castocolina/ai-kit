## Reviewer cursor-sol
### Document Type
superpowers · plan (both documents)

### CRITICAL
- **New setup prompt breaks existing interactive fixtures** — Location: Provisioning Task 6, lines 670–690 and 943–946. Required: update every interactive setup helper, especially `run_setup_with_numbered_selection`, to supply a deterministic System One answer before GPU/model selections. Why: the new prompt consumes the first existing selection line, contradicting the claim that pre-existing setup tests remain unchanged.
- **Successful-response fixtures violate the retained response contract** — Location: Decision Task 4, lines 594–598, 673–705; Task 7, lines 1238–1245. Required: include `"type": "noul"` in every mocked noul answer expected to succeed. Why: `_check_noul_answer` requires this field, so the planned success and fallback tests instead produce `invalid_response`.
- **Kill switch and consent can be bypassed through published interfaces** — Location: Decision Global Constraints, lines 29–37; Task 3, lines 510–548. Required: enforce `GSD_PATH_JEV=1` and remote consent at the dispatch/send boundary, or make these helpers explicitly private and inaccessible outside a gated path with tests proving no bypass. Why: the plan promises that nothing is sent without both gates, while direct `send()` or `dispatch()` calls transmit without either.
- **Parallel evaluation lanes share non-isolated log counters** — Location: Decision Task 8, lines 1295–1388. Required: serialize the live lanes or isolate each lane’s requests and log accounting. Why: both lanes query the same `system-one` logs concurrently, so each lane can count the other lane’s POSTs and fail checks expecting exactly three or zero requests.

### HIGH
- **GPU status becomes factually wrong in System-One-only mode** — Location: Provisioning Architecture and Review Focus 3, lines 7–9 and 40–47. Required: add `scripts/gpu-status.sh` and its tests to the implementation scope so `llm_server.enabled: false` does not report “no GPU is in use” when System One is enabled. Why: the existing command exits with exactly that incorrect result.
- **Twenty-six calibration cases are delegated rather than specified** — Location: Decision Task 5, lines 946–968. Required: provide all 32 exact JSONL records or an exact deterministic generator and expected output. Why: implementer-authored cases materially change measured accuracy and the calibrated fallback threshold.
- **The required writing-skills workflow is incomplete** — Location: Decision header and Tasks 1, 6, and 7. Required: incorporate the mandatory writing-skills checklist items, including its required TDD background, per-item tracking, wording micro-tests, red-flags section, quick reference, and common-mistakes coverage—or explicitly mark justified items inapplicable. Why: the plan claims to follow writing-skills but omits mandatory parts of that on-disk workflow.

### MEDIUM
- **OpenCode retry branches lack coverage** — Location: Decision Task 4, lines 741–808. Required: test 5xx and network-error fallthrough to the paid model and prove 401/403 do not fall through. Why: these are explicit backend-contract branches implemented without regression tests.
- **The live VRAM gate does not guarantee config restoration** — Location: Provisioning Task 11, lines 1466–1492. Required: install an EXIT trap immediately after creating the backup and restore/restart through that trap. Why: failures before the explicit copy-back can leave `llm_server.enabled` changed despite the plan’s “whether comparison passes or fails” guarantee.

### Cross-Document Consistency
- No additional cross-document contradiction found; both plans consistently gate live skill work on Provisioning Task 11 leaving Laya healthy at `127.0.0.1:8010`.

### Status: Issues Found — fix and re-invoke

## Reviewer cursor-glm
### Document Type
superpowers · plan (both documents)

### Files Read
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (1510 lines)
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (1410 lines)
- Grounding (read for verification, not review): `scripts/start.sh`, `tools/lib.sh`, `pylib/config.py`, `pylib/compose.py`, `pylib/resources.py`, `pylib/budget.py`, `scripts/check-setup.sh`, `scripts/check-server.sh`, `setup/setup.sh`, `tests/test_shell.py`, `~/.claude/skills/jev-fast-decision/scripts/jev_review.py`, `~/.claude/skills/jev-fast-decision/SKILL.md`

### MEDIUM

- **VRAM gate config restore not robust to early failure** — Location: Plan A, Task 11 Step 5 (lines 1470-1490). Required: restore the config backup even when a command before the `cp "$backup" "$config"` line fails under `set -euo pipefail` (e.g. `make start` nonzero, `uv run llmenv.py detect` failure, or the `curl` gate). Why: the block states "Restore the original config afterwards, whether the comparison passes or fails," but the unconditional `cp` sits after several commands that can exit the shell under `set -e`, leaving `llm_server.enabled: false` / `system_one.enabled: true` persisted on the host. A `trap 'cp "$backup" "$config" 2>/dev/null; rm -f "$backup"' EXIT` (or an explicit `restore() { ...; }` called before every `die`/early exit) after the `cp "$config" "$backup"` line is the minimum fix.

- **No test for `print-endpoints.sh` System One output** — Location: Plan A, Task 7 (lines 1077-1087) modifies `scripts/print-endpoints.sh` to print the System One endpoint and skill env vars. Required: add a `tests/test_shell.py` case asserting that with `system_one.enabled: true` the script prints the `http://127.0.0.1:8010/v1/systemone` line and `JEV_BACKEND=laya` / `JEV_LAYA_URL=...` skill hint, and that with `system_one.enabled: false` neither appears. Why: Task 7 adds tests for `start.sh` image/weights/health gating but leaves the endpoint display untested; `make status` is the operator's primary discovery surface and the decision-skill plan (Plan B) depends on the printed `JEV_LAYA_URL` hint being correct.

### Cross-Document Consistency

- Both plans agree on the live gate: Plan A Task 11's last step leaves `system_one.enabled: true` with healthy `http://127.0.0.1:8010`; Plan B Tasks 5 (live eval), 7, and 8 consume that state and check `curl -sf http://127.0.0.1:8010/health` before proceeding. The dependency is stated identically in both headers. No drift detected.
- Both plans use the same Laya wire facts (model `jev-1` request → `laya-rl-agent` response, `/health` shape, 4-decimal probability rounding, ~12 ms latency, per-item dispatch to avoid state contamination). Consistent.
- Plan B's `backends/laya.md` content spec (Task 6) and `reference.md` batching rewrite both defer to Plan A's `make start` / `system_one.enabled` / `system_one.port` for the Laya endpoint. Plan A's `print-endpoints.sh` (Task 7) emits exactly the `JEV_LAYA_URL` hint Plan B's docs describe. Consistent.

### Status: Issues Found — fix and re-invoke

## Reviewer cursor-gemini
### Document Type
superpowers · plan
### CRITICAL
- **Execution Order Contradiction** — Location: `docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (Execution order vs Task 6). Required: Resolve the circular dependency/contradiction where the execution order claims Task 6 runs *without* Laya, but Task 6 Step 1 copies from `eval-results.json` (produced by Task 5, which requires Laya) and Task 6 Step 3 explicitly tests that "Laya is up, so the agent uses laya". Why: Execution order must accurately reflect dependencies; running Task 6 without Laya will fail.
### HIGH
- **Non-actionable Steps (Documentation)** — Location: `docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (Task 10) and `docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (Task 6). Required: Provide the exact markdown text to write/insert for documentation updates, not just high-level bullet points (e.g., "what it is; endpoint/env", "Topology diagram: fourth box"). Why: A plan must be executable by a zero-context engineer with exact code/text, not high-level directions that require design choices by tooling.
### MEDIUM
- **Missing Rollback** — Location: `docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (Task 11 Step 5). Required: Ensure `models.yml` is restored (e.g. via `trap 'cp "$backup" "$config"' EXIT`) if `uv run llmenv.py detect` or the arithmetic expansion fails mid-script. Why: If the script crashes before the manual `cp "$backup" "$config"`, the user's config is left in a broken/test state.
### Cross-Document Consistency
- **Execution Order Synchronization** — Location: `docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (Execution order). Required: Update the execution order note to match the fix for Task 6 above (Task 6 requires Laya and Task 11). Why: The provisioning plan mirrors the decision-skill plan's execution order and currently shares the same incorrect assumption about Task 6.
### Status: Issues Found — fix and re-invoke

