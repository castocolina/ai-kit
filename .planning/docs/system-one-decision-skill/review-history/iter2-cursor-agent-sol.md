## Review: 2026-10-10-system-one-provisioning.md; 2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### CRITICAL
- **Decision plan assumes unavailable Git history** — Location: decision plan, Task 0 Step 1, lines 50–57. Required: identify an existing immutable Zen-only snapshot or use only the no-skill baseline, with commands valid for the authoritative non-Git skill directory. Why: the proposed `git show`/`git log` workflow cannot execute in that location.

### HIGH
- **Configured GPU is not proven ROCm-capable** — Location: provisioning plan, Tasks 3, 6, and 9, lines 338–474, 751–849, 1127–1166. Required: setup must verify that the selected PCI device and readable render node are ROCm-capable before enabling System One, and `check-setup` must repeat that exact mapping check with hybrid-GPU tests. Why: global `/dev/kfd` existence does not prove the generically detected, selected render node belongs to an AMD ROCm GPU.
- **Incomplete cache can pass startup validation** — Location: provisioning plan, Tasks 6, 7, and 9, lines 818–848, 961–983, 1143–1164. Required: define one shared required-asset manifest and make setup, start, and check-setup verify every required config, tokenizer, encoder, and weight file; test partially populated caches. Why: prefetch downloads four asset classes, but start and check-setup verify only `model.safetensors`, permitting an unplanned startup download or failure.
- **Probe failures disappear from backend reports** — Location: decision plan, Review Focus 2 and Task 4, lines 42 and 502–534. Required: retain probe-time `unavailable` reasons in successful and failed screening results, with a test where Laya’s probe fails and TypeSafe returns 429. Why: Laya is removed by `candidates()` before dispatch, then the returned result omits `unavailable`, contradicting the requirement to report both failures.
- **Laya test stub violates the response contract** — Location: decision plan, Tasks 2 and 5, lines 144–162 and 551–574. Required: generate normalized choice probabilities for every allowed option count and complete score responses containing `legend` and `probabilities`; cover all three answer types. Why: the required mixed-type evaluation will reject the proposed score response, while choice sums are valid only for exactly three options.
- **Per-backend confidence selection lacks an executable contract** — Location: decision plan, Global Constraints and Tasks 4/7, lines 33, 439–534, 608–610. Required: specify how the selected backend supplies its default threshold, validate `JEV_MIN_CONFIDENCE` as finite and within `[0,1]`, define structured failure behavior, and test invalid values plus backend-specific defaults. Why: Task 4 retains one module-level `MIN_CONFIDENCE`, while Task 7 requires per-backend defaults and leaves malformed environment values able to raise during import.

### MEDIUM
- **Baseline repetition count is contradictory** — Location: decision plan, Task 1 Step 2, line 104. Required: state either 25 no-skill runs (`5 scenarios × 5 reps`) or define the additional repetitions producing 50. Why: the written multiplication yields 25, not 50.
- **VRAM gate does not calculate aggregate usage** — Location: provisioning plan, Task 11, lines 1277–1287. Required: provide a command that totals System One’s unique DRM-client VRAM and compares it programmatically with `vram_reserve_mib`. Why: raw `rg` matches from every fdinfo file do not establish the claimed ≤4096 MiB result.

### Cross-Document Consistency
- **Live Laya dependency has no declared execution order** — Location: provisioning plan Tasks 7/11 and decision plan Tasks 5/6. Required: declare that provisioning through a healthy port 8010 endpoint precedes the decision plan’s live evaluation, or define an independent fixture. Why: the decision plan otherwise depends on an ad-hoc service that the provisioning plan explicitly removes.

### Status: Issues Found — fix and re-invoke
