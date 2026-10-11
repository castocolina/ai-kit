## Review: 2026-10-10-system-one-provisioning.md, 2026-10-10-system-one-decision-skill.md
### Document Type
superpowers · plan (both documents)

### HIGH
- **Runtime dependency is undeclared** — Location: Provisioning Task 9, lines 1352–1362. Required: remove the runtime `sd` dependency or add it to prerequisite and tooling checks. Why: `make prerequisites` does not install or verify `sd`, so `make check-setup` can fail on a valid installation.
- **Live evaluation can silently calibrate from incomplete data** — Location: Decision-skill Task 5, lines 1203–1247; Task 8, lines 1420–1423. Required: fail unless all 32 cases return `status: ok`, and assert `n == 32` before recording or calibrating. Why: unavailable cases are currently skipped, allowing thresholds and final metrics to use a partial dataset.

### MEDIUM
- **GPU vendor detection lacks a direct test** — Location: Provisioning Task 6, lines 672–679 and 790–794. Required: add `tests/test_detect.py` coverage proving `list_gpus()` reads `device/vendor` and handles a missing vendor file. Why: shell tests stub the `vendor` result and cannot catch an incorrect sysfs implementation.
- **Log-count gates are timestamp-racy** — Location: Decision-skill Task 8, lines 1401–1430 and 1484–1509. Required: isolate each request count without second-resolution wall-clock overlap. Why: `date ... +%SZ` can include a preceding request from the same second, causing false failures for expected counts of zero or three.

### Cross-Document Consistency
- No cross-document contradictions found.

### Status: Issues Found — fix and re-invoke
