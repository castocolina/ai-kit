# Loop 39.1.3 round 1 fixes: ai-kit-spec-config

Round 1 left 4 high findings (referee-one D8-1 to D8-3, the Opus substitute for referee-three D8-1; referee-two A 95.2
had none), more than 3, so each was checked against the text and code, fixed, and round 2 judges the result. The goal is
grade A, so the mediums the three judges share (body size, eval fixtures, a default for `policy.mode`) and the cheap lows
are fixed too. No product code changed; no feature was removed.

- referee-one D8-1 (high), `SKILL.md:120`: the check-only branch probed without asking when every profile was read-only.
  SKILL.md and `references/check-only.md` now ask before any live probe, every time, with "skip the probe" first/default,
  naming the allowance it spends and the runner state it keeps; a skip reports each lane as unknown.
- referee-one D8-2 (high), `references/check-only.md:64`: consent could cover a different argv than the probe ran. The
  preflight snippet now prints every field of a custom entry (`fields`, the values that fill its placeholders), the owner
  sees them, and the re-run compares every printed value. A recorded scratch run (`tmp/judge-39.1.3/verify_r1.sh`) shows
  a user-layer custom lane printed with its extra `level` field. The one limit left (an edit between that re-run and the
  probe's own resolve) is stated.
- referee-one D8-3 (high), `SKILL.md:37`: the NEVER list gave `REVIEW/EXECUTE` as the `purpose` literals; it now names
  `review`, `execute` and `both`, lowercase as the writer stores them.
- Opus D8-1 (high), `references/runtime-ids.md:21`: "research it per SKILL.md Step 2.2's rule" pointed at no rule and
  invited a model-specific search. It now sends the agent to `cli-model-selection.md` item 2 (ask the owner; web names
  only through `web-query` and `record-web-names`), and decides from `detect-runtimes` output instead of an undated codex
  command claim (referee-one D8-5, Opus D8-3: the codex bare-id rule now says Step 2.5's test checks the installed binary).
- referee-one, referee-two, Opus D5-1 (medium): Step 1.6's sorting procedure moved to `references/skill-role-sorting.md`
  (read only after the owner agrees to sort); Step 4's command-bearing definition is now a pointer to the one definition
  in `references/config-file.md`; the repeated `unknown` annotation rule, the Step 3 target restatement and the Step 4
  "single vague sentence" prose were shortened. SKILL.md went from 442 to 420 lines.
- referee-one D7-1, Opus D7-1 (medium): six evals gained input files under `evals/files/` (existing local roster, global
  roster, pending old roster, the unconfirmed opencode profile with a scripted skip, and a catalog plus a fresh listing for
  the stale-row case); the check-only eval names what must stay unchanged and the new always-ask rule.
- referee-one D8-4 (medium): `cli-model-selection.md` item 4 now shows a `confirm-catalog-entry` payload with the five
  required fields; the recorded scratch run above confirms it (`{"confirmed": true}`); a missing required value means no
  entry and another model or the session default.
- referee-one D6-1 (medium): `catalog.md`'s `models-config` calls take `--cwd "<project root>"`, and a `[models]` change
  is a separate, named write with the owner's yes (`--global` only for the user layer).
- referee-two D6-1, Opus D6-1 (medium/low): Step 2.8 makes `single` the first/default `policy.mode` (the reader's default).
- Opus D8-2 (medium): the claude alias session-default pair goes through Step 2.5 like any pair before it is saved.
- Lows: NEVER reasons for the herdr, data-use and flag items (Opus D3-1); description now leads with the user's goal
  (all three D4-1, 1013 characters); trigger queries swap two easy negatives for near-misses and add a casual positive
  (referee-one D7-2, Opus D7-2); `wizard-flow.md` step 9 weighs quota before fixing an order (referee-two D2-1).

Test modules updated with the changed sentences: `tests/test_cross_ai_docs_text.py` (Step 1.6 reads the new reference),
`tests/test_role_orders.py` (the snippet's `fields` and the new listing sentence).
