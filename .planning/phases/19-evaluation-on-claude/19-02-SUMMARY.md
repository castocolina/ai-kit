# 19-02 Summary: pressure-harness fixtures and headless runner

**Built the `fixture` (scenarios B, C, D, E) and `run` subcommands of the eval helper, with 97 unit tests passing and the four eval files written. The live model runs (`run` against real `claude -p`) were not executed.**

## Accomplishments

- `fixture B|C|D|E --run-dir` builds each scenario hermetically from the seeded caches. All four builds exit 0. B and D record `v1_listing_isolated: true` and `v1_entrypoint_pinned: true`. Every cell records the skill digest `551234cc5f4f55cc`, matching 19-01.
- `run --cell red-a|red-b|green` drives the scripted `claude -p` turns through `runner_dispatch.child_env`. It records per-turn init fields, cost, and the transcript dir, then deletes the scratch transcript.
- Process supervision: each turn runs in its own session, timeouts are SIGTERM then SIGKILL on the group, and `_reap_strays` kills run-dir processes outside the harness's own ancestry.
- Turn gating: a non-zero exit, a missing result event, or `is_error` stops the scripted continuation as an infrastructure failure, so the cell is never graded.
- Harness checks: non-empty `skills`, `slash_commands` or `mcp_servers`, a non-strict tool set, a `~/.claude.json` projects key for the scratch dir, a Skill tool_use, and an entrypoint shadowing the cell's own skill copy.
- Four eval files under `skills/ai-kit-gsd-curated-config/evals/`, with check names and kinds for 19-03's grader. Scripted-answer counts match the spec: B 2, C 0, D 2, E 2.
- 97 unit tests in `tests/test_gsd_curated_eval.py` cover `TestRun` and `TestFixture`, including the three cycle-3 tests, all passing.

## Verification

- `python3 -m unittest tests.test_gsd_curated_eval -k TestRun -k TestFixture`: OK.
- `tools/run_unittest_parallel.py --group unit`: 42/42 modules passed.
- `ruff check` and `ruff format --check` on both modules: clean.
- `pyright` on both modules: 0 errors.
- The non-vacuity checks were confirmed by mutation: disabling the launcher's PATH prepend makes the PATH-decoy test fail, and mutating a runtimes file breaks the byte-identity check.

## Files Created/Modified

- `tests/gsd_curated_eval.py` (modified): fixture section, `fixture` and `run` subcommands.
- `tests/test_gsd_curated_eval.py` (modified): `TestRun`, `TestFixture`.
- `skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md` (new)
- `skills/ai-kit-gsd-curated-config/evals/02-opencode-routers-no-catalog.md` (new)
- `skills/ai-kit-gsd-curated-config/evals/03-v1-written-config.md` (new)
- `skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md` (new)
- `.planning/phases/19-evaluation-on-claude/19-02-SUMMARY.md` (new)

## Issues Encountered

- **Not run: live model cells.** No `claude -p` turn was executed against a real model, so no cell has a graded outcome. The `run` path is verified only with a stub `claude` binary.
- **D premise mismatch.** The plan assumed the real v1 flow writes a `model_policy` key. It does not: the v1 flow writes no `model_policy`. D's facts were rewritten to check `model_overrides`/`models` unsets with non-null `existing` values instead.
- **Test-design corrections.** Three tests were initially vacuous or wrong and were corrected: the version test pointed at a missing binary, the probe test skipped the claude-row step the real build runs, and the launcher's non-vacuity decoy emitted no models so a reached probe was invisible. Each now asserts a discriminating observable.
- **Pylint not gated on tests.** `pylint` gates only `tools/` and `skills/`. It reports style findings in `tests/gsd_curated_eval.py` (too-many-locals, import-outside-toplevel, a lambda assignment). These are outside the gate and were not fixed here.
- **Leftover processes not mine.** Two `gsd-tools.cjs run-with-timeout ... cross-ai.mjs` processes, started about 741 s before this check, belong to a separate cross-AI session. Left running; not this task's.

## Commits

- Pending: `test(19-02): ...` (single logical commit, to be made after this summary is reviewed).
