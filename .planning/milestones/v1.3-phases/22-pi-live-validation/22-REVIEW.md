---
phase: "22"
depth: standard
reviewer: "cross-AI opencode router-env/my-plan-review (code) + ponytail pass (same lane)"
diff_base: e3c1b93
status: fixed
findings: { critical: 0, high: 1, warning: 4, info: 0, low: 2 }
fixed_in: [a53569b, cbf7214, 5262e92, 8bfa224]
---

# Phase 22 — Code Review

Reviewed `git diff e3c1b93..HEAD -- . ':!.planning'` through the cross-AI lane, with a ponytail
pass on the same lane. Fixes ran on pi (router-env/my-coding); the orchestrator re-read each diff
and re-ran `make test` and `make validate` on the fixed tree.

## Dispositions

- Ponytail HIGH, a hand-edited `pi.sonnet` bypassing the provider check at apply: one shared
  `plan_io.pi_sonnet_value_problem()` now gates `plan-set`, `apply --dry-run` and `apply` before
  any write (a53569b).
- WR-01 symlinked snapshot root traversed into credential files: a symlinked root hashes its
  link target string only (8bfa224).
- WR-02 malformed pi RPC input: `ValueError`/`RecursionError` caught, and a non-blank non-JSON
  line now returns the structured failure (locked D-04/R1); the plan-era noise-tolerance test
  that encoded the old skip was updated (cbf7214).
- WR-03 L3b-only steering verdict: a live verdict needs a passing L3a or L3c; the self-test
  covers the L3b-only case and the runbook sentence matches (5262e92).
- WR-04 / ponytail MEDIUM explicit installer dir of another version: the `_install_local()`
  version check is shared and applied to an explicit `--installer-dir` (8bfa224).
- Ponytail LOW: `TemporaryDirectory(ignore_cleanup_errors=True)` in the parallel runner, and the
  pi smoke chain reads the live tables once (8bfa224).

## Reviewer reports (verbatim)

## Findings

### WR-01: Pi snapshot hashing can follow a root symlink into credential files
**File:** tests/gsd_curated_eval.py:325-327  
**Issue:** The new pi tree checks call `_tree_sha()`, which checks symlinks only below the supplied root. If `~/.pi/agent/extensions` is itself a symlink to another directory, `root.is_dir()` and `os.walk(root, followlinks=False)` still traverse that starting directory. For example, `extensions -> .` makes the snapshot read and hash `auth.json`, `models.json`, and session files despite the documented exclusion.
**Fix:** Check `root.is_symlink()` before `root.is_dir()` and hash the link target string without traversing it. Add a synthetic test with a symlinked tree root and a credential-shaped file that must never be opened.

### WR-02: Malformed RPC input can crash enumeration or be accepted as success
**File:** skills/ai-kit-spec-review/ai_kit_spec/detection.py:494-497  
**Issue:** Only `JSONDecodeError` is caught. On Python's default integer-conversion limit, a response containing a 5,000-digit `maxTokens` value raises `ValueError` and escapes enumeration instead of producing the structured failure. Conversely, `not JSON\n` followed by a successful empty response returns `[]`, hiding malformed output. The latter matches the implementation plan's noise-tolerance test but contradicts locked SPEC R1/D-04, which requires a non-JSON line to produce a structured error.
**Fix:** Catch JSON decoding failures, including `ValueError` and `RecursionError`, and return `None` rather than continuing past malformed nonblank lines. Keep unrelated valid JSON events permissible. Add regression tests for the oversized integer and mixed malformed/successful output.

### WR-03: An override-absent L3 run can earn a live steering claim
**File:** .planning/phases/22-pi-live-validation/live/check_pi_live.py:65-67  
**Issue:** Any optional row marked `pass` permits the verdict `session-steer (live L3 ...)`. With all required rows passing, `L3b=pass`, and both `L3a` and `L3c` declined, the checker accepts that upgraded verdict. L3b explicitly runs without an override, so it cannot prove that steering works. This conflicts with locked D-03's evidence ladder; the later runbook's “an L3 row passed” instruction is too broad.
**Fix:** Require a passing override-enabled arm (`L3a` or `L3c`) before accepting a live steering verdict. Keep L3b as the independent baseline, not evidence of steering. Add the L3b-only case to the checker’s self-test.

### WR-04: The pi matrix can combine different gsd-core versions and report a pinned pass
**File:** tests/gsd_curated_eval.py:1013-1021  
**Issue:** Automatic package lookup checks the version, but an explicit `--installer-dir` or `ctx.installer_dir` only needs to contain `pi/gsd.cjs`. Supplying a package from another version runs its hook against the selected resolver and still reports the resolver's version in `gsd_core.version`. A green matrix can therefore certify a combination that was never shipped together, contrary to the inherited pinned-gsd-core validation contract.
**Fix:** Read the selected package's `package.json` and require its version to equal the tools version before running any probe, matching `_install_local()`'s existing check. Add a mismatch-refusal test for an explicitly supplied package.

COUNTS critical=0 warning=4 info=0

## Ponytail pass (verbatim)

## What this change does

Phase 22 extends pi model enumeration with exact token limits and reasoning levels, and offers an opt-in, provider-scoped session model override. It adds pi hook probes, matrix/smoke coverage, and protection checks while correctly keeping pi’s “not live-validated” label pending the owner’s interactive run. I reviewed this for the repo’s stated single-user workload.

### Must fix

1. **HIGH — The new model restriction disappears at apply time**  
   `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:495–510`

   `plan-set` rejects a value outside `roles.pi_session_ids()`, but a hand-edited plan bypasses that check. Set the value to `router-env/my-coding` and remove `status`: `plan_io._validate_entry_value()` has no pi rule, `check_plan_inventory()` checks only host/trusted roots, and apply’s encoder accepts the string. The inventory digest does not protect plan entries. This can install the exact value the new guard warns would break every session request.

   **Smallest fix:** share the provider-membership check between plan editing and the plan/inventory validation used by apply. Add one regression proving both dry-run and real apply reject the edited plan before writing.  
   **Estimated saving:** **0 lines**; this needs missing validation, not a cut.

### Should fix

2. **MEDIUM — An explicit installer directory bypasses the pinned-version check**  
   `tests/gsd_curated_eval.py:1012–1020`

   Automatic discovery uses `_cached_installer(version, home)`, which checks `package.json`. Supplying `--installer-dir` checks only that `pi/gsd.cjs` exists. Consequently, the matrix can resolve models using one gsd-core version, probe another version’s hook, and report only the resolver’s version as its evidence.

   **Smallest fix:** reuse the package-version validation already performed by `_install_local()` at `tests/gsd_curated_eval.py:4205–4212`. Reject an explicit directory whose version differs from `tools_path`; keep the offline directory option.  
   **Estimated saving:** **approximately 0 lines overall** if the existing validation is shared.

### Nice to have

3. **LOW — Manual temporary-directory cleanup duplicates the stdlib**  
   `tools/run_unittest_parallel.py:143–158`

   `mkdtemp()` plus an outer `try/finally` and `shutil.rmtree()` exists solely to manage the per-module scratch directory. `tempfile.TemporaryDirectory(..., ignore_cleanup_errors=True)` already supplies that lifetime and preserves the current cleanup-error policy.

   **Smaller change:** use that context manager, retaining the subprocess timeout handler and all three temporary-directory environment variables. Remove the now-unused `shutil` import. The new cleanup regression remains useful unchanged.  
   **Estimated saving:** **about 4 lines**.

4. **LOW — The pi smoke chain reads the same live tables twice**  
   `tests/gsd_curated_eval.py:4482–4485`, `tests/gsd_curated_eval.py:4455–4456`

   `_baked_chain()` invokes `live_tables()` and sorts the agent names before dispatching to `_pi_chain()`. That function immediately repeats both operations. Each pi scratch-project check therefore starts an unnecessary second Node subprocess.

   **Smaller change:** move the pi dispatch ahead of `_baked_chain()`’s table lookup. The pi branch retains its own lookup, agent count, hook check, and generated-file checks; other hosts remain unchanged.  
   **Estimated saving:** **0 lines**, but one subprocess and one redundant sort per chain check.

**Verdict:** fix 1 and 2 first. None of these changes removes a required feature.

Not checked: tests, live pi behavior, or owner-only evidence; this was a static, read-only review with no AI CLI, network, or protected-config reads.

PONYTAIL high=1 medium=1 low=2
