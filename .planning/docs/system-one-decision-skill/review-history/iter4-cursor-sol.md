## Review: 2026-10-10-system-one-provisioning.md, 2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### CRITICAL
- **Automatic fallback can transmit local data remotely without consent** — Location: decision-skill Global Constraints lines 31–33; Task 4 lines 504–519 and 613–637. Required: prevent remote dispatch until explicit consent is represented in executable state, or return a consent-required result before switching from Laya to TypeSafe/OpenCode. Why: Laya can pass the probe and fail during dispatch, after which the loop silently sends the same payload off-machine.
- **Request receipt contract cannot be implemented from the defined interfaces** — Location: decision-skill Task 3 lines 374–381, 432–486. Required: define how encoded request bodies are returned or recorded, including exactly which attempted bodies are hashed when sequential Laya dispatch fails partway through. Why: `dispatch()` returns only responses and specs, while `screen()` must hash the exact bodies `send()` transmitted—even on failure.

### HIGH
- **Transient cache containers lack required SELinux handling** — Location: provisioning Task 6 lines 899–905; Task 7 lines 1040–1047; Task 9 lines 1285–1292. Required: add the repository bind mount with Fedora-compatible relabeling such as `:ro,z`, or explicitly disable labeling for every prefetch/verify invocation. Why: the existing compose implementation documents relabeling as required on Fedora, but these commands mount the checker with only `:ro`.
- **`check-setup` still validates skipped llama.cpp model files** — Location: provisioning Task 9 lines 1157–1297. Required: condition or skip the existing “Model files” GGUF validation when `llm_server.enabled` is false, with a regression test using absent model files. Why: the current block is unconditional, so the required System-One-only mode can fail despite setup intentionally skipping model downloads.
- **The labeled evaluation set and evaluator remain placeholders** — Location: decision-skill Task 5 lines 655–699. Required: provide all labeled cases and the complete `eval_cases.py` implementation, including deterministic per-case data generation for `eval-results.json`. Why: the executor must invent at least 28 labels and substantial scoring logic that directly determines calibrated thresholds.
- **Baseline pressure-test dispatch is not reproducible** — Location: decision-skill Task 1 lines 89–107. Required: specify the exact dispatch command/tool, model, prompt assembly, isolation, concurrency, and verbatim result-capture method for both 25-run arms. Why: “dispatch 50 subagents” is not executable by a zero-context engineer.
- **External evaluation failures can be mistaken for completed lanes** — Location: decision-skill Task 8 lines 859–887. Required: capture each background PID, verify each exit status, and require a non-empty report ending in `VERDICT pass|fail` before producing findings. Why: bare `wait` does not reliably gate each job, and unavailable models or CLI failures can leave empty report files.

### MEDIUM
- **Architecture documentation scope leaves known contradictions** — Location: provisioning Task 10 lines 1357–1397. Required: update the topology, service-count prose, named-volume diagram/table, persistence behavior, and `system-one-cache` entry in the compose example—not only the files table and one paragraph. Why: the current architecture document explicitly describes three services and two named volumes.
- **The VRAM acceptance gate measures the entire restarted stack** — Location: provisioning Task 11 lines 1413–1430. Required: isolate the System One container’s before/after allocation or otherwise exclude llama.cpp and other restarted GPU consumers. Why: the measured delta is not specifically attributable to System One and can produce a false failure.

### Cross-Document Consistency
- **Task 8 has contradictory prerequisites** — Location: provisioning plan line 3; decision-skill plan lines 3 and 772–788. Required: state consistently that decision-skill Task 8 requires completed provisioning and healthy Laya. Why: the provisioning plan says Task 8 does not require Laya, while the decision-skill plan makes Laya a hard precondition and stops when health fails.

### Status: Issues Found — fix and re-invoke
