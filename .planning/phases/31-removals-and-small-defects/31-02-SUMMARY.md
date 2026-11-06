---
phase: 31-removals-and-small-defects
plan: 02
subsystem: spec-review
tags: [check-providers, opencode, spec-config, read-only-report, jsonc]
requires: []
provides:
  - "ai-kit-spec.py check-providers [--cwd DIR]: read-only stale opencode provider report (SPEC R5)"
  - "spec-config Step 1 runs the report in setup and --check-only (non-blocking)"
affects: [ai-kit-spec-review, ai-kit-spec-config]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/provider_check.py
    - skills/ai-kit-spec-review/ai_kit_spec/jsonc_read.py
    - tests/test_ai_kit_spec_check_providers.py
    - tests/test_ai_kit_spec_jsonc_read.py
    - skills/ai-kit-spec-config/evals/evals.json
    - skills/ai-kit-spec-config/evals/trigger-queries.json
    - skills/ai-kit-spec-config/evals/files/stale-opencode/review-spec.toml
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-config/SKILL.md
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "served providers: the live opencode listing decides; config files count only when the listing fails, and then every warning is marked unconfirmed"
  - "an untrusted project-local review-spec is reported inactive and cannot deactivate the global file"
  - "reads only provider ids and the reviewer/catalog model reference; auth.json is never opened"
metrics:
  tasks: 3
  commits: 3
  duration: "about 20 min"
status: complete
requirements: [RMV-02, JDG-04]
actuals:
  tokens: 35815
  tasks: 3
  commits: 3
---

# Phase 31 Plan 02: check-providers stale opencode provider report Summary

`check-providers` reports each review-spec or catalog reference to an opencode provider that the live
listing does not serve (or, unconfirmed, the config files do not define), read-only and non-blocking,
and spec-config runs it in setup and `--check-only`.

## Commits

- `02c892a` feat(31-02): check-providers reports stale opencode providers in review-spec (Tasks 1 and 2)
- `dbe7ac0` docs(31-02): spec-config runs check-providers in setup and --check-only (Task 3)
- `a78aa05` test(31-02): type-clean check-providers test fakes for pyright (pyright fix, own change)

## Verification

- `tests.test_ai_kit_spec_check_providers`: 19 tests ok (tracer, sources, trust, fallback, secret, SKILL.md, evals count)
- `tests.test_ai_kit_spec_jsonc_read`: 3 tests ok (drift against `tools/config_doctor_readers.py` on 5 fixtures, non-vacuity)
- `tests.test_ai_kit_spec`, `tests.test_arch`, `tests.test_skill_evals_shape`, `tests.test_gate_scope`: ok
- `make pyright`: exit 0 (after `a78aa05`)
- `make ruff`, `make pylint`: pass
- `make test` (through `scope.py test`, one run): exit 0. Tiers: unit 99/99, unit-uv 1/1, integration 8/8,
  e2e 25/25, `tests/test_install.sh` 45 passed 0 failed, arch 1/1.
- Acceptance greps: `provider_id in` 0; `"check-providers"` in cli.py 2; `resolve_runtime_binary` 2;
  unconfirmed qualifier 1; `check-providers --cwd` in SKILL.md 2; empty-listing label 1.

## Deviations from Plan

1. **Tasks 1 and 2 share one commit (`02c892a`).** Both tasks write `provider_check.py` and `jsonc_read.py`
   once; splitting them would have meant writing a throwaway intermediate module. The commit carries the
   Task 1 tracer and every Task 2 source, trust, fallback and secret case.
2. **Task 3 evals changed beyond `files: []`.** The shared evals-shape test requires a
   `trigger-queries.json` (16 to 24 queries) and at least one input file under `evals/files/`. Added both,
   with one synthetic `review-spec.toml` attached to the stale-provider case. The global-file prompt was
   reworded because the machine-path rule flags `~/`.
3. **`scan_review_spec` signature.** The plan named a one-argument scanner. It takes `env` and `gate_trust`
   and returns `(status, refs, data, trusted)`, so the local file is read once and the trust gate applies to
   the local file only.
4. **Known gap, not fixed:** when `HOME` and `XDG_CONFIG_HOME` are not absolute, `cfg_global_path` raises
   `ConfigError`, and `main` exits 2 instead of the plan's "exits 0 whatever it finds". Left as found; the
   sibling subcommands behave the same way.
5. **Commit ledger (protocol 0c) not written** before the first commit. `plan_head_before` is the recorded
   base `a9747a44ec66df8b86ca9f5e6bd8fcaa2ebe974b`, and `commits` counts from that base.
6. **Requirements not marked complete.** `REQUIREMENTS.md` was not touched: the orchestrator owns the
   shared planning writes while wave-1 agents run in parallel.

## Known Stubs

None.

## Threat Flags

None. The report reads provider ids and the reviewer/catalog model strings only; it opens no network
path and writes nothing.

## jev calls

None made in this run. The decisions listed under Deviations (combining the Task 1 and 2 commit, the
input file and trigger queries, the widened signature) were made by the executor without jev. The plan
left no 2-4 option choice open, so no jev request was sent.

## Orchestrator steps

- orchestrator step: skill-judge loop (native opus xhigh) on `skills/ai-kit-spec-config/` (SKILL.md, `evals/evals.json`,
  `evals/trigger-queries.json`, `evals/files/`). Run it from the repository root until no critical or high
  finding remains and the grade is B or better, then record the verdict, the evals and
  `tests/test_ai_kit_spec_check_providers.py` in `31-VERIFICATION.md`.

## Self-Check: PASSED

- Created files exist: `provider_check.py`, `jsonc_read.py`, both test modules, `evals/evals.json`,
  `evals/trigger-queries.json`, `evals/files/stale-opencode/review-spec.toml`.
- Commits are ancestors of HEAD: `02c892a`, `dbe7ac0`, `a78aa05`.
