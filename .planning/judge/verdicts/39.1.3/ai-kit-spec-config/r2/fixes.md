# Loop 39.1.3 round 2 fixes: ai-kit-spec-config

Round 2 left 5 high findings, all from referee-one (D6-1, D8-1 to D8-4; referee-two A 96.0 and referee-three B 87.2 had
none), more than 3, so each was checked against the text and code, fixed, and round 3 judges the result. The shared
medium (body size) and the cheap mediums and lows are fixed too. No product code changed; no feature was removed.

- referee-one D6-1 (high), `SKILL.md:199`: a "replace" answer bound to the path, not the roster the owner saw. Step 2.1
  now keeps what the gate showed, and Step 3 reads the target (with any old roster pending migration beside it) again
  right before `render-toml`; a changed roster, other than by a migration an approved step made, goes back to the gate.
  The one gap left (a change between that read and the write) is stated.
- referee-one D8-1 (high), `SKILL.md:130`: a stale-provider-only request fell through to the snapshot save and setup.
  Step 1 now routes it to `check-providers`, relays its certainty labels and stops with no save, catalog, question or write.
- referee-one D8-2 (high), `references/check-only.md:93`: probe results were matched to raw-read lanes by key alone. Each
  result is now reported against the entry the preflight snippet printed (role, runtime, model, command); a raw-read lane
  whose same key is overridden by the other layer is `available: unknown (not probed — overridden ...)`.
- referee-one D8-3 (high), `SKILL.md:402`: the short command-bearing summary dropped the `local-only` exception. It now
  counts the user layer only without `strategy = "local-only"` and points to `config-status` for the actual state.
- referee-one D8-4 (high), `references/wizard-flow.md:73`: "no run reads them yet" was wrong for the escalation flags:
  `runner_dispatch.py` passes `--escalate-runtime`/`--escalate-model` and `cross-ai.mjs` reports them as ignored
  (`recorded_only`) without starting another lane. `wizard-flow.md`, `config-file.md` and the escalation eval now say
  that; `usage_limited` keeps "no run reads it" (only the writer and `lane_settings` readers touch it).
- referee-one D5-1, referee-two D5-1, referee-three D5-1 (medium): Step 2.7's routing background, nested-host precedence
  and entry shapes moved to `references/session-default.md` (MANDATORY read at Step 2.7); the gotcha and the ask stay.
- referee-three D8-1 (medium): when Step 0 finds no `ai-kit-spec-review`, the skill names the three folders tried and asks
  the owner for an installed one before stopping.
- referee-one D7-2 (medium): the stale-catalog eval relays whatever attribution lines `catalog-report` prints instead of
  requiring lines the fixture cannot produce.
- Lows: a reason for the hand-written-command NEVER item (referee-three D3-1); Step 3 checks each lane's place in its
  order against quota and strength once before building the JSON (referee-two D2-1).

Left for a later loop: the router-alias eval's either-way assertion (referee-one D7-1), splitting Step 2.5's test
paragraph (referee-three D8-2), and the remaining lows. Test modules updated with the changed sentences:
`tests/test_spec_config_flow_text.py` (escalation line, Step 2.7 alias via the reference),
`tests/test_ai_kit_spec_check_providers.py` (escalation phrase), `tests/test_ai_kit_spec_runtimes_table.py` (the pair-rule
paragraph now lives in `references/session-default.md`).
