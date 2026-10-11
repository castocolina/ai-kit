## Review: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md; /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md
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
