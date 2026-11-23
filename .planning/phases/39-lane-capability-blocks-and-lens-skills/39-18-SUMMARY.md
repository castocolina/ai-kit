---
phase: 39-lane-capability-blocks-and-lens-skills
plan: 18
subsystem: judge
tags: [skill-judge, loop-39, jdg-04, referee-one, referee-two]

requires: [39-17]
provides:
  - "Loop 39 records for ai-kit-spec-review and ai-kit-spec-config (rounds 1 to 3) and ai-kit-cross-ai and ai-kit-gsd-curated-config (round 1), judged by referee-one and referee-two only; REJUDGE.md and facts.json regenerated"
  - "All four skills meet the bar (grade B or better) in every round with no regression beyond judge variation; cross-ai and curated-config fixed under the no-rejudge rule; spec-review and spec-config end round 3 with 4 and 5 open high findings, recorded as they stand for the owner"

key-files:
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - .planning/judge/loops/39.json
    - .planning/judge/verdicts/39/
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/check-only.md
    - skills/ai-kit-spec-config/references/cli-model-selection.md
    - skills/ai-kit-spec-config/references/wizard-flow.md
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review/references/apply-findings.md
    - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
    - tests/test_ai_kit_spec_runtimes_table.py
    - tests/test_role_orders.py
    - tests/test_ai_kit_spec_check_providers.py
    - tests/test_cross_ai_docs_text.py

requirements-completed: [JDG-04]

executor: "orchestrator action in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and router-env/my-referee-two through the project runner, review mode, --host none"
---

# Phase 39 Plan 18: Loop 39 skill-judge loop

Commits (pre-fold): records r1 `ae9798a`; fixes r1 `24136c5` (cross-ai), `f6f659e` (curated-config), `f782c59` (spec-config), `793a26b` (spec-review); records r2 `4910768`; fixes r2 `48ef8de` (spec-config), `b497ed5` (spec-review); records r3 `0365007`.

## Judged set

`tmp/judge-39/judged.py` (`judged self-check: ok`) uses base `d06064a^` (the commit that added 39-01-PLAN.md). Changed SKILL.md files: ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-spec-config, ai-kit-spec-review (the same four as `git diff --stat 04fd6ca..HEAD -- skills/*/SKILL.md`). Fact-only: none. `judged-decisions.txt`:

- `ai-kit-cross-ai judged`: beyond the template number 11 to 12, two passages add a caller-facing output contract (the `cross-ai: capabilities <JSON>` line of `--print-argv`).
- `ai-kit-gsd-curated-config judged`: beyond the template number 11 to 12, a new step line (classify-skills, confirm-skill-role on the user's acceptance).

`skills.r1.txt`: all four. ai-kit-spec-review-checklist and ai-kit-spec-execute-superpowers have no SKILL.md change in this phase and were not judged (their stale digests are notes).

Scratch: `tmp/judge-39/` (loop id `39`). The drivers were copied from `tmp/judge-38.1/` with `38.1` replaced by `39`, digit-bounded (`retry cap: ok`, `no native pool: ok`, `judges: ok`, `timeout: ok`, `round scope: ok`, `compile: ok`). Scoped changes as the plan names them: `legacy_retry_check.py` (HOME from the environment, stripped XDG, every `.planning/**/config.json`), `lanes.py count --no-jev`, `findings.py` (refutation skip and one count per judge and finding id). Legacy-retry preflight before every round: `legacy retry: none`.

## Loop 39 bar results

| Skill | Round | Worst percent | Grade | Bar | Prior base | Findings (crit+imp+high) | decide.py row | Outcome |
|---|---|---|---|---|---|---|---|---|
| ai-kit-cross-ai | 1 | 84.8 | B | met | loop 38.1: 83.2 | 1 | fix, `24136c5` | bar met, then fixed under the no-rejudge rule |
| ai-kit-gsd-curated-config | 1 | 81.6 | B | met | loop 38: 85.6 | 3 | fix, `f6f659e` | bar met, then fixed under the no-rejudge rule |
| ai-kit-spec-config | 1 | 80.0 | B | met | loop 37: 84.0 | 5 | next-round, fixed `f782c59` | |
| ai-kit-spec-config | 2 | 84.8 | B | met | loop 37: 84.0 | 4 | next-round, fixed `48ef8de` | |
| ai-kit-spec-config | 3 | 84.0 | B | met | loop 37: 84.0 | 5 | owner-round-3 | bar met; 5 findings open after round 3 (owner) |
| ai-kit-spec-review | 1 | 81.6 | B | met | loop 36: 83.2 | 5 | next-round, fixed `793a26b` | |
| ai-kit-spec-review | 2 | 84.8 | B | met | loop 36: 83.2 | 4 | next-round, fixed `b497ed5` | |
| ai-kit-spec-review | 3 | 82.4 | B | met | loop 36: 83.2 | 4 | owner-round-3 | bar met; 4 findings open after round 3 (owner) |

The bar authority is `judge_loop.py`'s `bar_with_base` row in REJUDGE.md (every row `met: grade B or better`). `regression.py` lines (informational):

- r1: cross-ai `lowest 84.8, loop 38.1 r3 base 83.2, delta +1.6, regression: no`; curated-config `lowest 81.6, loop 38 r1 base 85.6, delta -4.0, regression: no`; spec-config `lowest 80.0, loop 37 r3 base 84.0, delta -4.0, regression: no`; spec-review `lowest 81.6, loop 36 r2 base 83.2, delta -1.6, regression: no`.
- r2: spec-config `lowest 84.8, ... delta +0.8, regression: no`; spec-review `lowest 84.8, ... delta +1.6, regression: no`.
- r3: spec-config `lowest 84.0, ... delta +0.0, regression: no`; spec-review `lowest 82.4, ... delta -0.8, regression: no`.

No regression beyond judge variation: the worst delta is -4.0 against the 7.0-point floor. Every fixed finding is listed in its round's `fixes.md` under `.planning/judge/verdicts/39/<skill>/r<N>/`.

Not refuted, kept: ai-kit-spec-review D5-1 (body size; rounds 1 to 3). The remedy (moving the role, refusal and lens-note tables and the after-approval pass out of SKILL.md) breaks the locked contract: 39-SPEC.md:670 and tests/test_cross_ai_docs_text.py:243-266. It needs a SPEC amendment by the owner. No refutation file was written: no finding was shown wrong by a recorded run. spec-review r1 D8-2 was confirmed by a recorded run (`capability-block ... --files <path outside the repository>` exited 65 with `path_outside_roots`) and fixed.

## Open findings after round 3 (owner questions)

`loop 39: ai-kit-spec-config has 5 findings after round 3; decide`:
- referee-one D8-1 references/catalog.md:31: the catalog fetch omits `--cwd "<project root>"`, and the keep-backup choice is not carried to every fetch form.
- referee-one D8-2 SKILL.md:388: the lane objects do not carry the resolved or confirmed `vendor`.
- referee-one D8-3 SKILL.md:367: the single and double wording does not match `resolve_reviewers`, which prefers a different vendor.
- referee-one D8-4 SKILL.md:305: `config-status` shows the effective roster, not every saved lane.
- referee-two D8-1 references/check-only.md:16: the snippet routes every lane with the review host context, so "exactly the keys probe-quota spawns" is not proven for execute lanes.

`loop 39: ai-kit-spec-review has 4 findings after round 3; decide`:
- referee-one D5-1 SKILL.md:290: body size, blocked by the SPEC contract above.
- referee-one D6-1 SKILL.md:549: `rm -rf "$RUN_TMP_DIR"` does not check that the path belongs to this run.
- referee-one D8-1 references/apply-findings.md:9: a fused superpowers design routes by archetype, not by the owning `doc_types` row.
- referee-one D8-2 SKILL.md:178: `probe-quota` skips native and skipped routes and reuses fresh cached rows, so not every lane is probed.

## Loop 39 facts for the verifier

- Judges: referee-one `opencode:router-env/my-referee-one` and referee-two `opencode:router-env/my-referee-two`, the configured pair. The ledger `tmp/judge-39/ledger.md` holds `p39-18 judges: referee-one, referee-two` and the live judge calls authorization line. Probes, both usable: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=14s out=2165 tree=clean ... attempts=1 cycles=0` and `... model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=21s out=2210 tree=clean ... attempts=1 cycles=0`, each with `cross-ai: setting host=none applied`. Pool `39`: both members; native null; no substitutes; count 2 per skill (`--no-jev`, deterministic); `loop record: ok`.
- Lanes: 16 lanes in 3 rounds (8, 4, 4), all `ok` on the first attempt. No failed or rejected lane, no relaunch, no referee-three.
- `verdict_facts.py` verdicts (percent, grade, critical, high): cross-ai r1 84.8 B (0, 1) and 88.8 B (0, 0); curated-config r1 81.6 B (0, 3) and 88.8 B (0, 0); spec-config r1 80.0 B (0, 5) and 92.0 A (0, 0), r2 84.8 B (0, 4) and 91.2 A (0, 0), r3 84.0 B (0, 4) and 91.2 A (0, 1); spec-review r1 81.6 B (0, 5) and 90.4 A (0, 0), r2 84.8 B (0, 4) and 85.6 B (0, 0), r3 82.4 B (0, 4) and 88.8 B (0, 0).
- `check.py` (`--require-current`) exited 0 in each round before that round's fix commits, with the digest current.
- Scoped gate before the r1 fixes: `gate.sh` (`judge_loop.py check .planning/judge --skills ai-kit-cross-ai ai-kit-gsd-curated-config --judges native:opus-xhigh opencode:router-env/my-referee-one opencode:router-env/my-referee-three opencode:router-env/my-referee-two --require-current --gate`, every judge id on disk) exited 0. Rounds 2 and 3 had no record or fix skill, so the gate was skipped.
- Closing check: `closing.sh` (`judge_loop.py check .planning/judge`) exited 0 after the last commit, with a `: loop 39` line per judged skill: spec-config `round 3 ... worst 84.0 B; critical 0; high 4; bar met ...; digest current`, spec-review `round 3 ... worst 82.4 B; critical 0; high 4; bar met ...; digest current`, cross-ai and curated-config `round 1 ... digest stale`.
- `make check-dogfood` before each records commit: `check-dogfood: ok` (no-write guard 3 attempted, 3 executed, 0 skipped). `stale_after.py`: `stale ok` each round. `evals_gate.py`: `evals gate: ok`. `tests.test_skill_evals_shape`: 1/1 before each dispatch. `decide.py --self-check`: `decide self-check: ok`. `bar_table.py`: `regex self-check: ok`, `unmet.txt: 0 skill(s) not met` each round. `pool_check.py` before and after: ok each round. Fix commits ran the plan's test set and their commit hooks passed (793a26b and b497ed5: 141/141 modules, the 12 self-test shards included).

## Stale-digest notes

- Stale before the loop: ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-usage-metrics, jev-fast-decision.
- Stale by design after the r1 fix commits (`tmp/judge-39/intentional-stale.txt`): ai-kit-cross-ai, ai-kit-gsd-curated-config. `report` was not re-run for them. ai-kit-spec-config and ai-kit-spec-review are current (judged again after each fix).

## Mtime check of the listed paths

`mtime check of the listed paths: changed .cursor/cli-config.json`. The snapshot (8 labels, 5 files present) was taken before the probes. `.cursor/cli-config.json` has mtime 2026-11-23 14:05:34, inside the round 1 lane window. The judge lanes are opencode only, no cursor-agent process was running at the compare, and the mtime did not change again in rounds 2 and 3. The cause is unknown and not attributed (owner item). The lanes ran with the caller's real HOME, the plan's named exception. This claim covers only these stat results and the legacy-retry preflight.

## Deviations

- All four changed SKILL.md files were judged. The plan's two OPTIONAL decisions both read `judged` (the cross-ai capabilities passage is more than a substitution).
- spec-review D5-1 was kept unchanged in rounds 1 and 2 and stays open, as described above (advisor-checked; not filed as a refutation).
- Fix commits changed four test modules whose pinned text changed: `test_node_floor`, the check-only snippet placeholder in `test_role_orders` and `test_ai_kit_spec_check_providers`, and the quoted `--files` form in `test_cross_ai_docs_text`. Each pin keeps or strengthens its assertion.
