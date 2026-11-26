# Loop 39.1.3 round 3 fixes: ai-kit-spec-config

Round 3 left 3 high findings, all from referee-one (D8-1 to D8-3; referee-two A 98.4 and referee-three B 87.2 had none),
3 or fewer, so by AGENTS.md's judge-loop rule each was checked against the text and code and fixed in the skill's own
files, and no further judge round runs (round 3 is also the cap): the skill's digest is stale by design until its next
loop. Two cheap mediums are fixed too. No product code changed; no feature was removed.

- referee-one D8-1 (high), `SKILL.md:120`: the headless stop promised no write while detection itself can touch disk.
  Checked in `ai_kit_spec/detection.py`: `_private_dir` creates ai-kit's cache folder for the opencode listing's private
  working directory (removed afterwards by `_opencode_private_dir`), and a CLI may update its own files while it lists.
  SKILL.md and `references/headless.md` now state that limit; no ai-kit config, snapshot, catalog or trust record is
  written.
- referee-one D8-2 (high), `references/trust-flow.md:40`: step 7 compared only key and argv for rendered entries, so a
  changed field that moves no argv (a `vendor`) could be trusted. Step 3 now keeps every field of each command-bearing
  entry, and step 7 re-reads the file after the trusting call and compares every field of every command-bearing entry,
  revoking on any difference.
- referee-one D8-3 (high), `references/wizard-flow.md:43`: the effort probe dropped the lane's other knobs. It now passes
  them with `--extra-json`, as Step 2.5's pair test does, so the level is tested with the settings the lane is saved with.
- referee-one D8-4 (medium): Step 3's `render-toml` example quotes `--out "<target path>"` and `--catalog-path "<catalog>"`
  (a path with spaces stays one argument); `tests/test_spec_config_flow_text.py` pins the quoted form.
- referee-three D8-1 (medium): the run line at the top now names Steps 1.5 and 1.6 and the four early stops of Step 1.

Left for a later loop: body size (all three D5-1; SKILL.md is about 6,600 words), `render-toml` checking a roster digest
under its lock (referee-one D6-1, a code change), the catalog optional-source routing (referee-one D2-1), eval and
trigger-query refinements (referee-one D7-1/D7-2, referee-two D7-1, referee-three D7-1), and the remaining lows.
