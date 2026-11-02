---
phase: "24"
depth: standard
reviewer: "cross-AI opencode router-env/my-plan-review (code) + ponytail pass (same lane), before the owner moved reviews to three reviewers"
diff_base: "HEAD of the shipped skill at review time (8c53d16)"
status: fixed
findings: { critical: 1, warning: 8, ponytail_high: 1, ponytail_medium: 4, ponytail_low: 3 }
fixed_in: [c14a753, dde6e12, 735af73, 6ab4f70, 86b6859]
---

# Phase 24 — Code Review

The skill `skills/ai-kit-gsd-spec-discuss/` and its tests were reviewed as they stood at HEAD.
The skill shipped early in 24-01 and was extended in 21.1. Fixes ran on pi, then on cursor auto
after a pi crash; that was the runner's automatic fallback, which the owner has since removed.
The orchestrator re-ran the gates: pyright 0, `make test`, `make validate` and `make e2e-docker`
all exit 0.

## Dispositions

- CR-01: item ids now pass the secret guard before any payload or log line (c14a753).
- WR-01..WR-08 are fixed in dde6e12:
  - a bad item type fails only that item;
  - allowlisted values must match closed codes;
  - `decided_by` comes only from a validated non-fallback column;
  - a partial requirement extraction fails closed;
  - a malformed engine row exits 2;
  - a malformed or empty roadmap JSON is an error;
  - the real-engine e2e fails on zero coverage;
  - explicit selection wins over "skip current phases".
- Ponytail 2-8 are taken (dde6e12, 735af73). The duplicate client smoke test is removed and the
  amendment is dated in 21.1 D-20 / 24 D-13.
- 6ab4f70 and 86b6859 keep tty and PTY tests off the ambient `AI_KIT_REFUSE_REAL_HOME` guard.
- The skill-judge rounds that followed (r0-r3, PASS at 7fc3f03ffb2fb714) are in
  `24-SKILL-JUDGE.md`. The remaining Importants are in backlog 999.11.

## Reviewer reports (verbatim)

## Findings

### CR-01 — Item IDs bypass the secret guard and reach remote payloads and logs

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:155–172`

**Issue:** `id` is checked only for a nonblank string and the reserved `#` prefix. Unlike instructions, context and criteria, it never passes through `_bad_text()`. A valid item whose ID is `"sk-" + "x"*30` passes validation. The shared client includes that ID in remote request bodies and its persistent answer log; `decide.py` also prints it as a result key. This defeats the explicit no-secret transmission/output rule through an otherwise schema-valid field.

**Fix:** Apply the length, code-fence and secret-pattern checks to IDs before dispatch. Key a rejected unsafe ID by `#<index>` rather than echoing it in the rejection. Add a test asserting that a synthetic secret-shaped ID reaches neither the client payload nor stdout, stderr or the answer log. This implements, rather than changes, locked D-11 and SPEC R6.

### WR-01 — Malformed item types crash the entire batch

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:166`

**Issue:** Membership in `ITEM_TYPES` assumes the supplied type is hashable. Valid JSON containing `"type": []` or `"type": {}` raises `TypeError` instead of rejecting that item alone. One malformed analyzer item therefore loses all valid siblings and produces exit 1 with a traceback. The existing rejection tests use only an unsupported string (`"box"`), so they miss this branch.

**Fix:** Require `type` to be a string before set membership. Test array and object types alongside a valid sibling, asserting a per-item rejection, preserved sibling processing and exit 0, as locked D-07 requires.

### WR-02 — Field-name allowlists do not enforce the promised no-leak output boundary

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:314–328`

**Issue:** Client-provided `error` and `model` strings are copied without validation. The same problem exists for status, probe and consent fields: `closed_status()` is not actually a closed-set check, and `public_consent()` accepts any scalar `reason` or `note`. A compatible-but-leaky client returning a credential in `error` or `reason` has that value printed verbatim. The current leaky-client tests put secrets only in excluded `debug_env` fields, proving field filtering but not the stated guarantee.

**Fix:** Validate reason/status codes against the supported vocabulary and constrain model and label fields to their documented shapes; replace unexpected values with fixed errors. Extend the fake-client tests to leak a synthetic sentinel through allowed fields, not just extra fields. This follows locked D-06’s closed-set failure rule.

### WR-03 — A rejected answer can still be reported as the deciding backend

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:347–376`

**Issue:** `fill_columns()` validates each answer through `typed_answer()`, but computes `decided_by` independently from the raw trail. A rung with an unknown choice, `top: 0.9` and `needs_fallback: false` produces:

```json
{"laya": {"error": "invalid_response"}, "decided_by": "laya"}
```

The decision table tells the agent to take an answer when `decided_by` names that backend, despite its only column being an error. Numeric validation also accepts `NaN`, infinity and out-of-range probabilities.

**Fix:** Select the deciding backend only from successfully validated columns. Require finite probabilities in `[0, 1]`, a boolean fallback flag and an answer matching the item’s type. Add malformed-trail tests asserting that invalid answers cannot win. This preserves Phase 21.1 D-11’s “last confident rung” contract.

### WR-04 — Partial requirement extraction silently weakens the coverage floor

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py:27–43`

**Issue:** Only numbered entries with bold titles start a requirement. For example:

```markdown
1. **Parse rows**.
   - Target: parse rows.

2. Write cache.
   - Target: write atomically.
```

Extraction returns only `R1`, absorbing requirement 2 into its text. Because the list is nonempty, the fail-closed check passes and no independent `R2` floor is computed. Duplicate numbered bold entries similarly produce duplicate IDs without rejection. Tests cover zero extraction, but not partial extraction or duplicate IDs.

**Fix:** Keep locked D-22’s documented bold-title grammar, but reject numbered requirement entries that do not match it and reject duplicate IDs before calling the engine. Add fixtures for both cases. No extraction-format change is needed.

### WR-05 — Malformed engine rows escape the fail-closed exit contract

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py:126–129,146–149,186`

**Issue:** Engine validation checks only that `items` is a list. Responses such as `{"items":[{}]}` or `{"items":[null]}` pass that check, then raise `KeyError` or `TypeError` in `compare()`. That call is outside the exception handler, so `check` exits 1 with a traceback—the same code documented for ordinary coverage drift—instead of exit 2 with a fail-closed diagnostic.

**Fix:** Validate each engine row’s required string fields before returning from `run_engine()`, and keep comparison failures within the fail-closed handler. Add malformed-row tests distinguishing exit 2 from legitimate drift’s exit 1. This implements locked D-22.

### WR-06 — Roadmap JSON can silently mean “nothing to do” or crash outside error handling

**File:** `skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py:97–103,123–134`

**Issue:** JSON syntax is checked, but its structure is not. An error object such as `{"error":"engine failed"}` returns a successful empty proposal, indistinguishable from all phases being current. A top-level array or `{"phases":[null]}` instead raises `AttributeError` outside the handler. Invalid phase selectors are also converted into the shared `(sys.maxsize,)` sentinel rather than rejected.

**Fix:** Validate the top-level object, required `phases` list, phase entries, numeric phase identifiers and selector bounds before proposing anything. Return a concise error with exit 2 for invalid input. Add CLI tests for error objects, malformed entries, invalid selectors and reversed ranges.

### WR-07 — The real-engine test passes when the engine returns no coverage

**File:** `tests/test_ai_kit_gsd_spec_discuss_e2e.py:15–19`

**Issue:** The sole assertion checks that returned requirement IDs are a subset of `{"R1", "R2"}`. An empty `items` list satisfies it. The test would therefore pass if the engine stopped producing every floor row. It also never runs `check`, so it does not verify the extraction-to-table contract. Separately, all phase-selection tests replace `git_time()` with a dictionary lookup, leaving its real git/mtime behavior untested.

**Fix:** Assert concrete expected category/requirement pairs for the fixture, then verify that removing an expected table row causes drift. Add an isolated git-history fixture for equal commit times, a later SPEC commit and untracked-file mtime fallback. These tests preserve locked D-18’s git-time policy rather than substituting filesystem timestamps.

### WR-08 — Explicit selection conflicts with the final instruction to skip current phases

**File:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:223–224`

**Issue:** Setup says an explicit range or list wins, and `phase_range.py` deliberately proposes current phases when explicitly requested. The final instruction nevertheless says to skip a phase whose SPEC and CONTEXT are current and not load its references. An agent explicitly asked to revisit such a phase receives incompatible instructions about whether to run it.

**Fix:** Restrict the final skip instruction to automatic proposals: skip current phases **unless explicitly requested**. Add a prose-contract assertion covering that exception. This resolves the contradiction in favor of the explicit-selection rule without changing locked D-18’s completed-phase exclusion.

Not checked: full suites, installed backends or live workflows; verification used read-only source inspection and in-memory checks, with no network calls or fixture files created.

COUNTS critical=1 warning=8 info=0

## Ponytail pass (verbatim)

**What this change does:** The skill takes a range of GSD phases through specification and assumptions-mode discussion, with advisory backend answers, decision logs, and a deferred ledger. I reviewed committed sources at **HEAD `8c53d16`**, assuming the documented single-user workflow.

The wrapper, second-opinion flag, three item types, and standalone resolver are explicitly required—not speculative extras.

## Must fix

1. **HIGH — Item IDs bypass the secret guard** — `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:155–171, 189–192`
   - `instructions`, `context`, and criteria pass through `_bad_text`; `id` only needs to be nonblank and not start with `#`. A synthetic ID shaped like `<redacted-example>` passes, although the identical value in `context` is rejected. The shared client sends IDs in request state and records them in its answer log.
   - **Smaller change:** Validate IDs with the existing `_bad_text` helper. For rejected IDs, use the existing `#<index>` result key rather than echoing the rejected value.
   - **Estimated saving:** Reuses the guard instead of adding another sanitizer; roughly **4–8 added lines plus a regression test**. This enforces, rather than contradicts, locked **24 D-11** and SPEC R6.

## Should fix

2. **MEDIUM — An unhashable item type crashes the entire batch** — `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:166`
   - Both `"type": []` and `"type": {}` raise `TypeError` at membership in `ITEM_TYPES`. One malformed item therefore prevents valid siblings from proceeding. I reproduced this directly against the HEAD function.
   - **Smaller change:** Check that `type` is a string before set membership. Add both inputs to the existing mixed-batch test.
   - **Estimated saving:** **One guard line**, preserving the batch without a new exception-handling layer. This restores locked **24 D-07**’s per-item rejection rule.

3. **MEDIUM — Winner selection ignores the answer validation it just performed** — `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:347–376`
   - `fill_columns` validates each answer, then `decided_by` separately scans the raw trail. A rung with an unknown choice and `needs_fallback: false` produces `{"local":{"error":"invalid_response"},"decided_by":"local"}`. The decision table then directs the model to take that backend’s answer.
   - **Smaller change:** Select the winner during the existing mapping loop, using only a successfully mapped answer with `fallback is False`. Delete the separate raw-trail scan.
   - **Estimated saving:** Approximately **5–8 net lines and one traversal per item**. No locked-decision conflict: **21.1 D-11** requires the last *confident answer*, not an invalid response.

4. **MEDIUM — The real-engine test passes when the engine returns nothing** — `tests/test_ai_kit_gsd_spec_discuss_e2e.py:18–19`
   - The subset assertion accepts `{"items":[]}` because an empty set is a subset of `{"R1","R2"}`. The only real-engine test can stay green after losing the entire floor.
   - **Smaller change:** Replace `<=` with `==` so the fixture must produce coverage entries for both extracted requirements.
   - **Estimated saving:** **No additional lines**; one operator change makes the existing engine invocation meaningful. Consistent with locked **24 D-22**.

5. **MEDIUM — The validation-parity test lets the implementation choose what gets tested** — `tests/test_ai_kit_gsd_spec_discuss.py:457–480`
   - The client builder runs only when `decide.item_error(item)` accepts an item. If the wrapper starts rejecting every item in this table, the test passes without checking anything. This is circular coverage, not a mock problem.
   - **Smaller change:** Give each case an expected accepted/rejected value and assert it before calling the real client builder for accepted cases.
   - **Estimated saving:** **No extra subprocesses or fixtures**; roughly **3–6 net lines** remove the vacuous pass. Keeps locked per-item validation and the existing real-client check.

## Nice to have

6. **LOW — Backend implementation details are copied into the orchestrator’s instructions** — `skills/ai-kit-gsd-spec-discuss/SKILL.md:34–40, 136–142`; `skills/ai-kit-gsd-spec-discuss/references/decision-table.md:3–6`
   - The skill repeats key-source precedence, permissions, numeric thresholds, and backend size caps owned by the shared client. Adding a key source or changing a threshold requires editing unrelated orchestration prose too.
   - **Smaller change:** Keep the actionable consent/status instructions and forced-fallback handling. Link to `jev-fast-decision`’s reference for key discovery and current limits instead of copying their inventory.
   - **Estimated saving:** Approximately **100–150 words**, with fewer synchronized facts. No conflict with **21.1 D-22**: this is targeted trimming, not a full skill rewrite.

7. **LOW — Worked examples repeat their conclusions after already showing them** — `skills/ai-kit-gsd-spec-discuss/references/worked-examples.md:16–17, 28–29, 40–41, 52–53, 62–63`
   - The five “Lesson” paragraphs repeat rules already present in the mandatory decision table and main workflow. The useful material is the actual question, evidence, scores, and logged outcome.
   - **Smaller change:** Delete those five closing paragraphs; retain every worked example and its evidence.
   - **Estimated saving:** Approximately **100 words / 15 lines including spacing**. Preserves locked **24 D-14**’s worked examples.

8. **LOW — A client-only smoke test duplicates the client’s stronger existing test** — `tests/test_ai_kit_gsd_spec_discuss.py:638–643`
   - This test bypasses `decide.py` and asserts only that the client’s kill switch returns `disabled`. `tests/test_jev_fast_decision.py:525–536` already checks that result **and** proves stdin is not read and no POST occurs.
   - **Smaller change:** Remove `TestRealClientSmoke`; keep the stronger client-owned test and the many wrapper tests that invoke the real client.
   - **Estimated saving:** Approximately **8 lines and one Python subprocess per suite run**.
   - **Locked-decision conflict:** **21.1 D-20 explicitly retains `TestRealClientSmoke`**. Removing it needs a dated amendment; it should not be deleted silently.

**Verdict:** Fix **1–5** first. Keep the deliberate standalone resolver copy: its packaging purpose is documented and its candidate order already has a drift test.

Verification was limited to HEAD source review and in-memory checks; no files, git state, network, AI CLIs, or real auth/config were touched. Full suites were not run, so orchestration behavior remains unverified.
PONYTAIL high=1 medium=4 low=3
