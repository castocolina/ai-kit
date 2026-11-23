---
phase: 36-spec-config-as-the-hub
plan: 13
subsystem: spec-config
tags: [propose-lanes, ranking, zero-price, jev-seam, effort-levels]

requires: [36-02, 36-05, 36-06, 36-07, 36-09, 36-10]
provides:
  - "propose_cmds.py: `propose-lanes --purpose review|execute --catalog-path P (--detect | --runtimes-json P2) [--runtime R]... [--jev] [--avoid-pool KEY]... [--skip RUNTIME:KEY]...` prints one JSON object (purpose, default_view, ranking, jev, stale_checked, pool, zero_price, aliases, wider, alternative, empty, message); it writes no config, catalog, lane or usability record"
  - "cli.py: CliDeps.score_judge_fn (default jev_names.score_judge), propose-lanes registration"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/propose_cmds.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_propose_cmds.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (597 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 13: propose-lanes

One commit (pre-fold): `6b019dd feat(36-13): propose ranked lanes` (3 files, +406 -4; the lane folded the three tasks into one commit, hook 115/115).

## Accomplishments

- `propose-lanes` builds rows (plan 36-06), prices them (36-07), gives each row only the effort levels the runner can pass (36-05, `listed_ids` built once per runtime), ranks with the scorer and an optional injected jev judge (36-09), and prints the pool, the zero-price group (at most 5, with `group_rank`), the alias group, the wider group and the alternative. `catalog_cmds.py` is unchanged.
- Errors exit 2 with named messages (empty catalog, unreadable runtimes snapshot, bad `--skip`, bad `--avoid-pool`); an empty pool exits 0 with `empty` true.
- 17 tests in `tests/test_propose_cmds.py` (`TestProposeLanes` 14, `TestProposeReadOnly` 3): shape, execute pool, zero group cap, jev confident, low, absent, runtime filter, alternative filters, bad filters, effort levels, malformed numbers and listing, listed-ids once, empty cases, no-write proof, `--detect` through the seams only, closed-fact jev items.

## Deviations and notes

- The lane made one commit for the three tasks instead of one per task; the content matches the plan. No file outside the plan's three paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_propose_cmds tests.test_ai_kit_spec tests.test_arch tests.test_arch_hardcoded_models`: exit 0, 4/4 modules (17, 693, 109 and 14 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read propose_cmds.py whole and the cli.py diff against the plan.
- Real-config audit (marker-c4-p36-w5): see the ledger.

## Self-Check: PASSED
