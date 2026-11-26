substitute for referee-three (owner rule 2026-11-24)

# Third lane: Opus substitute for referee-three, ai-kit-spec-config, loop 39.1.3 round 1

The third lane `opencode:router-env/my-referee-three` failed after its one retry: both attempts ended `status=ok exit=0`,
but `judge_loop.py ingest` refused each verdict because its judge field held a zero-width joiner after the first letter
(the same failure as loop 39.1 round 3 and loop 39.1.2 round 1). A fresh read-only `ai-kit-judge` subagent (model opus,
effort high at dispatch, clean context) was given only the lane prompt built by
`judge_loop.py prompt --judge native:opus-high` and the frozen tree at 0b38df1. Its verdict was ingested into the round
records with `--native-note`, `--replaces opencode:router-env/my-referee-three` and the failure as `--reason`; the
validated record is `native_opus-high.json` in this folder, and `native:opus-high` is registered as `pool.native` in
`loops/39.1.3.json`.

- Verdict: 108/125, 86.4 percent, grade B (rubric 5)
- Critical or high findings: 1
  - D8-1 high `skills/ai-kit-spec-config/references/runtime-ids.md:21`: "research it per SKILL.md Step 2.2's rule" points
    at a rule Step 2.2 does not hold and invites the model-specific search `cli-model-selection.md` item 2 forbids.
