## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Transient cache containers lack required SELinux handling** — Severity: HIGH. Status: addressed. Edit: Every prefetch and verify bind of `system-one-cache-check.py` is `:ro,z`, with tests asserting that suffix, and the prefetch script now matches laya 0.4.2 `Agent.__init__` (`BUNDLE_REPO`, `normalise_name`, `resolve_revision`, the same `allow_patterns`). Section: Task 6, Task 7, Task 9.
- **`check-setup` still validates skipped llama.cpp model files** — Severity: HIGH. Status: addressed. Edit: The Model files GGUF block is skipped when `llm_server.enabled` is false, and `run_check_setup_with_stubs` gains `real_gguf` so a regression test runs real `validate-gguf` against absent `first.gguf`/`second.gguf`. Section: Task 9.
- **Architecture documentation scope leaves known contradictions** — Severity: MEDIUM. Status: addressed. Edit: Task 10 now names the topology diagram, four-service count, persistence table and paragraph, and the `system-one-cache` compose example, not only the files table. Section: Task 10.
- **The VRAM acceptance gate measures the entire restarted stack** — Severity: MEDIUM. Status: addressed. Edit: The gate flips to `llm_server.enabled: false` and `system_one.enabled: true`, measures that stack, then copies the backup back and runs `make restart`. Section: Task 11.
- **Legacy tool usage** — Severity: MEDIUM. Status: addressed. Edit: The render-node parse uses `sd` instead of `sed`. Section: Task 9.
- **Task 8 has contradictory prerequisites** — Severity: cross-document. Status: addressed. Edit: Decision-skill tasks that do not need Laya are Tasks 0–4 and 6; Task 8 requires a healthy `http://127.0.0.1:8010`. Section: Execution order.
- **Contradictory Execution Order** — Severity: cross-document. Status: addressed. Edit: Same execution-order sentence; the decision-skill plan already required Laya for Task 8. Section: Execution order.

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
- **Automatic fallback can transmit local data remotely without consent** — Severity: CRITICAL. Status: addressed. Edit: Remotes are candidates only when `JEV_ALLOW_REMOTE=1`; otherwise auto stays on laya and a laya failure returns `consent_required_for_remote` with `remote_available`, and an explicit remote backend without that variable does not send. Tests, Global Constraints, Task 6 guidance, and Task 8 checks 5, 8, and 9 match. Section: Global Constraints, Tasks 2, 4, 6, and 8.
- **Request receipt contract cannot be implemented from the defined interfaces** — Severity: CRITICAL. Status: addressed. Edit: `send()` returns `(response, encoded_body)`; `dispatch()` returns `(responses, specs, sent_bodies)`, appending each body before `send()` and raising `DispatchError` with those bytes; `screen()` hashes `sent_bodies`. Section: Task 3 Interfaces and Step 3, Task 4.
- **`dispatch()` interface insufficient for `request_sha256` contract** — Severity: HIGH. Status: addressed. Edit: Same return triple and hash, plus a test that a raised `send()` is still inside `request_sha256`. Section: Task 3 Interfaces and Step 3.
- **The labeled evaluation set and evaluator remain placeholders** — Severity: HIGH. Status: addressed. Edit: 32 cases (10 choice, 10 noul, 6 score, 6 shorthand; 5 ambiguous), the labeling rule, 6 exemplars, and the full `eval_cases.py` including `case_record` / `merge_results`. The other 26 lines are an execution step on purpose. Section: Task 5.
- **Baseline pressure-test dispatch is not reproducible** — Severity: HIGH. Status: addressed. Edit: Each rep is a fresh Claude Code `Agent` call (`general-purpose`, `sonnet`), prompt is the scenario alone or plus `Read` of the absolute `SKILL.md`, at most 5 concurrent, final message saved to `notes/baseline/<arm>-<scenario>-<rep>.md`. Section: Task 1.
- **External evaluation failures can be mistaken for completed lanes** — Severity: HIGH. Status: addressed. Edit: Each lane PID and exit status is captured; a non-empty report must end with `VERDICT pass` or `VERDICT fail` or the round stops. Part 1 uses skill-judge’s eight dimensions and the 16/12/8 floors. Section: Task 8.
- **Unverified `cursor-agent` model names in live evaluation** — Severity: MEDIUM. Status: addressed. Edit: Before round 1, `cursor-agent --list-models` must match `glm-5.2-max` and `gemini-3.1-pro` exactly. Section: Task 8 Step 3.
- **Task 8 has contradictory prerequisites** — Severity: cross-document. Status: addressed. Edit: The decision-skill execution order already required healthy Laya for Task 8; the provisioning sentence now says the same. Section: Execution order.
- **Contradictory Execution Order** — Severity: cross-document. Status: addressed. Edit: Same as the previous item. Section: Execution order.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Did not execute either plan or start a GPU container. The 26 non-exemplar case lines are still written at execution time; `test_cases_jsonl_composition` is what rejects a drift in counts or ambiguous ids.
