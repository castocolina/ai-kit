## Review: 2026-10-10-system-one-provisioning.md; 2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### HIGH
- **`screen()` implementation is incomplete and internally unordered** — Location: decision-skill plan, Tasks 3–4, lines 605–1007. Required: provide the complete `screen()` flow, including stdin parsing, kill-switch handling, provenance initialization, candidate selection, dispatch, hashing, and error returns; initialize `provenance` before its first use at line 909. Why: the supplied fragments cannot satisfy the Task 3 tests without inventing substantial order-sensitive code and currently reference `provenance` before any defined initialization.
- **Calibration corpus is not reproducible** — Location: decision-skill plan, Task 5, lines 1024–1048. Required: specify all 32 JSONL cases or provide a deterministic generator producing their exact text and labels. Why: the implementer must invent 26 cases whose contents directly determine measured accuracy and the production fallback threshold.

### MEDIUM
- **RAM-budget test is omitted from its commit** — Location: provisioning plan, Task 4, lines 575–588. Required: include the selected budget test file (`tests/test_budget.py` or `tests/test_cli.py`) in Task 4’s commit. Why: Step 3 requires this coverage, but Step 5 leaves it uncommitted.
- **Failed idle-CPU investigation has no rollback** — Location: provisioning plan, Task 8, lines 1163–1222. Required: if no candidate passes, restore `pylib/compose.py` and `tests/test_compose.py` to their pre-investigation state before stopping. Why: the current procedure leaves the final failed experiment in the working tree and can contaminate subsequent work.
- **Resource errors omit the newly reserved service** — Location: provisioning plan, Task 4, lines 552–568. Required: update and test `ResourceError` messages so thresholds that include System One identify its CPU/RAM reservation. Why: the proposed arithmetic increases the floors while existing diagnostics still attribute them only to the host, OmniRoute, remote-setup, and possibly llm-server.
- **Frontmatter example contradicts its required keywords** — Location: decision-skill plan, Task 6, lines 1258–1266. Required: make the example description include `needs_fallback` and consent, or remove it as a copyable example. Why: following the example violates the immediately preceding activation requirements.

### Cross-Document Consistency
- No additional inconsistency was found in the Task 11 dependency, Laya URL, model, or live-gate ordering shared by the plans.

### Status: Issues Found — fix and re-invoke
