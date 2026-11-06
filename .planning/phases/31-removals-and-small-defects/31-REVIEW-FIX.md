---
phase: 31-removals-and-small-defects
fixed_at: 2026-11-06T18:40:00Z
review_path: .planning/phases/31-removals-and-small-defects/31-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 31: Code Review Fix Report

Scope: every critical, high and medium finding (owner rule). Cheap low and info findings were
fixed in the same commits; the rest are listed with the reason. The orchestrator applied the
fixes directly (owner priority: speed) and triaged each finding with jev first, then checked it
in the code. No re-review iteration was run: the fixed set is small and each fix has its own
regression test.

## Fixed

| Finding | Severity | Commit | Fix and test |
|---------|----------|--------|--------------|
| CR-01 | high | 1b48f0a | `tools/command_ownership.py` compares `realpath` of both script paths, so a statusLine written through an alias spelling of the kit stays ai-kit's (detect, wire and uninstall all share this parser). Test: `TestStatuslineOwnershipCounterexamples.test_alias_spelled_line_stays_ours_on_both_hosts`. |
| WR-01 | medium | 1b48f0a | `_prune_headless` catches `OSError` per link, warns `could not remove dead ai-kit link ...` and goes on; `_headless_prune_roots` returns ok and `cmd_install_headless` folds it into the exit code. Test: `TestHeadlessPrune.test_unremovable_link_warns_and_the_run_goes_on`. |
| WR-02 | medium | 0be1acb | `served_providers` decides on the parsed provider ids: a listing with no `provider/model` line reports `not checked: opencode listed no models`. Test: `test_listing_without_model_lines_is_not_checked`. |
| WR-03 | low | 1b48f0a | `install.sh` resolves the kit dir with `CDPATH=''` and output discarded. `tests/test_install.sh` 48/0, shellcheck clean. |
| WR-06 | low (partial) | 1b48f0a | A dry run prints `would remove dead ai-kit link ...` (test `test_dry_run_says_would_remove`). The summary line does not yet count pruned links. |
| WR-08 | low | 0be1acb | Origin comments in `config_doctor_appliers.py` and `provider_check.py` no longer name deleted modules or line numbers. |
| IN-01 | info | 1b48f0a | Formatting slip `replaced =(` fixed. |
| T-31-04 (security audit) | medium | 0be1acb | `jsonc_read.read_provider_names` also catches `RecursionError`, so a deeply nested repo config fails soft. Test: `test_deeply_nested_file_returns_none`. |

## Not fixed (below the owner's bar)

- WR-04 (low): `check-providers` exits 2 on a relative `HOME`/`XDG_CONFIG_HOME`; already recorded as a known gap in 31-02-SUMMARY. Follow-up.
- WR-05 (low): the JSONC drift test compares behaviour on five fixtures and counts "both None" as agreement. Follow-up.
- WR-06 remainder (low): the headless summary does not print a pruned count.
- WR-07 (low): `git check-ignore` without `--`; out-of-repo link targets pass. The target comes from the repo's own AGENTS.md and the existence check runs first. Follow-up.
- IN-02 to IN-05 (info): unused `ReadContext.runner`, unreachable `ValueError` branch, rtk ban identifier forms, `config_get` `@file:` gap. Judgment calls, no defect today.

## jev triage

- cr01: supported, 0.73 (typesafe) -> verified in `command_ownership.py:61`, fixed.
- wr01: supported, 0.71, needs_fallback -> verified (`unlink_one` only suppresses `FileNotFoundError`), fixed.
- wr02: supported, 0.60, needs_fallback -> verified (`if listed:` tested the raw list), fixed.
