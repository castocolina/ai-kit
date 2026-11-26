# Loop 39.1.1 round 1 fixes: ai-kit-spec-config

Six critical, important or high findings (referee-one five, referee-two one; the advisory referee-three lane had none).
The owner's brief for this loop fixes every such finding after each round and runs the next round (target grade A), and
also fixes the medium findings that cost points when the fix is small and truthful. Every fix states only what the code
does (checked: `cli.py` `_cmd_trust_local`, `_cmd_check_reviewer`, `_cmd_render_toml`; `config_io.py`
`cfg_render_lanes`, `_cfg_lanes_policy`; `toml_splice.py` `set_array`; `model_catalog.py` `locked_catalog_update`,
`_current_catalog`; `detection.py` claude `native_selectors`). No code changed.

High:
- opencode:router-env/my-referee-one D8-1: the `--check-only` preflight snippet takes the review skill folder and the project root as argv (`sys.argv[1]`, `sys.argv[2]`), never inside its Python source, and a nonzero exit or no JSON list reports every key `available: unknown (the probe preflight failed)` with no probe. Files: `skills/ai-kit-spec-config/references/check-only.md`; the snippet tests read the argv form (`tests/test_ai_kit_spec_check_providers.py`, `tests/test_role_orders.py`).
- opencode:router-env/my-referee-one D8-2: Step 2.5 says `--extra-json` carries the non-effort knobs only, that `check-reviewer` refuses an effort together with `--catalog-path`, so the usability call tests the pair without its effort, and that the effort gets its own call (wizard-flow step 5). File: `skills/ai-kit-spec-config/SKILL.md`.
- opencode:router-env/my-referee-one D8-3: the no-catalog pending-roster case keeps the no-fetch rule but lets `confirm-catalog-entry` create the catalog from the owner's ids (it reads no roster); with no id it offers the session default as the only lane (no `--catalog-path` at Step 3, since `render-toml` refuses an unreadable path) or stops. Files: `skills/ai-kit-spec-config/references/catalog.md`, `skills/ai-kit-spec-config/SKILL.md` (Step 3).
- opencode:router-env/my-referee-one D8-4: the comment promise is qualified: comments of a lane entry or policy table the new roster drops go with it. Files: `skills/ai-kit-spec-config/references/config-file.md`, `skills/ai-kit-spec-config/SKILL.md` (Step 2.1 replacement ask).
- opencode:router-env/my-referee-one D8-5: Step 4 reports each item after `NOT written:` as printed (a rejected lane, or an order key or policy value) and never calls a dropped order key a dropped lane. File: `skills/ai-kit-spec-config/SKILL.md`.
- opencode:router-env/my-referee-two D8-1: `trust-local --show` records no new trust but first migrates a pending old roster (trust-flow step 1). File: `skills/ai-kit-spec-config/references/config-file.md`.

Medium and low, fixed because small and truthful:
- All three judges D1 (pattern label): the Process/Tool-level label sentence is replaced by the operative rule. File: SKILL.md.
- All three judges D3 (no Gotchas): a five-line Gotchas section after NEVER. File: SKILL.md.
- All three judges D4 (description): a `Not for` boundary, indirect wording, and no migration overpromise; 1024-character limit kept. File: SKILL.md.
- referee-one D6-2 (`--local` with `--global`): both flags together are asked about before anything else; Step 2.1 also reuses a target Step 1.5 already resolved (referee-three D8-2). File: SKILL.md.
- referee-one D5-1, referee-two D6-1, referee-three D5-1 and D1-1 (body size): Step 3's field-by-field list moved to `references/config-file.md` "Lane entry fields" (gated read at Step 3); the codex, cursor and custom-entry detail of Step 2.4 moved to the new gated `references/runtime-ids.md`; Step 2.8's timeout paragraph shortened. Files: SKILL.md, `references/config-file.md`, `references/runtime-ids.md`; `tests/test_spec_config_flow_text.py` reads the moved cursor sentence from the reference.
- referee-one D2-1: Step 1.6 says its role writes stand on their own; the Step 4 failure path lists them. File: SKILL.md.
- referee-one D8-6: scratch removed on every other ending, kept and named only after a failed write; web results go into `$SCRATCH`. Files: SKILL.md, `references/catalog.md`.
- referee-one D6-1: trust-flow step 5 makes "leave it untrusted" the default when an entry had no preview line of its own. File: `references/trust-flow.md`.
- referee-one D5-2, referee-two D5-1: wizard-flow step 2 reads items 1 to 4 only; cli-model-selection item 6 opens for every kept lane. Files: `references/wizard-flow.md`, `references/cli-model-selection.md`.
- referee-three D6-1: `strength` is offered once per run. Files: SKILL.md, `references/wizard-flow.md`.
- referee-three D8-1: the four claude aliases are named as ai-kit's native selectors; "pi today" wording replaced by the profile-file condition. Files: SKILL.md, `references/check-only.md`.
- referee-one D7-1, referee-two D7-1, referee-three D7-2 (evals): the router-alias eval reports the printed group either way and never ranks the roster's alias; the headless eval asserts no scratch folder. File: `evals/evals.json`.
- referee-one D7-2, referee-three D7-1 (trigger queries): legacy `review-spec` positives reworded to config.toml (the migration query kept), one indirect positive added, two easy negatives replaced by near misses. File: `evals/trigger-queries.json`.
