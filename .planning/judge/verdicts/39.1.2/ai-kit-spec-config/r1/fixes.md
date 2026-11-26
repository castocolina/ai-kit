# Loop 39.1.2 round 1 fixes: ai-kit-spec-config

Round 1 left 5 high findings (referee-one D8-1 to D8-4, referee-two D8-1; the Opus substitute for referee-three had
none), more than 3, so each was checked against the text and code, fixed, and round 2 judges the result. A few cheap
mediums and lows that cite real text are fixed too. No code changed; no feature was removed.

- referee-one D8-1 (high): SKILL.md's check-only line said the branch "stops with no writes", but a live probe runs
  through the cross-AI runner (`quota._probe_call` calls `run_runner`), whose real runs keep state under the state home
  and sweep dead runs. SKILL.md now says no config, cache, snapshot or trust write and names the runner's own state;
  `references/check-only.md` says the same where it defines "no writes".
- referee-one D8-2 (high): `references/wizard-flow.md` sent an empty-catalog exit back to Step 1.5 with no end. It now
  returns once; a catalog still empty after that refresh shows the fetch's failures and continues as the no-fetch case
  (owner-named ids through `confirm-catalog-entry`, else the session default or stop).
- referee-one D8-3 (high): the command-bearing definition named only the user config, but
  `config_io.cfg_project_trust_bytes` reads the user `config.toml` `[lanes]`, else a pending old `review-spec.toml`
  beside it (`_user_lanes_readonly`). SKILL.md Step 4 and `references/config-file.md` now name both.
- referee-one D8-4 (high): `references/cli-model-selection.md` named `~/.config/ai-kit/secrets.env`, but
  `local_secrets.secrets_env_path` uses an absolute `XDG_CONFIG_HOME`. The text now names the user config folder
  `${XDG_CONFIG_HOME:-~/.config}/ai-kit/` with that rule, or an environment variable.
- referee-two D8-1 (high): checked by a recorded scratch-HOME run (`tmp/judge-39.1.2/verify_tiers.sh`): a lane's flat
  `timeout_tiers = [900, 1800]` is written by `render-toml` (exit 0), carried by `quota.to_resolved` as
  `extra.timeout_tiers`, and `resolve-timeout-tiers` prints `900,1800` for it (`600,1200,1800` for a lane without one);
  a nested `extra = {...}` is rejected. The flat key works as written; Step 2.8 now says how dispatch reads it.
- referee-one D6-1 (medium): with every lane declined and no session default, Step 3 had no gate before a write that
  would empty the roster (a recorded run, `tmp/judge-39.1.2/verify_empty.sh`: an empty `lanes` list with `--replace`
  removes both role arrays). Step 3 now writes nothing by default and clears only on the owner's explicit request.
- referee-one D8-5 (medium): `references/free-lanes.md` section e now counts an added alternative as the fallback only
  once it is kept and not usage-limited itself, and asks again otherwise.
- Opus D8-1 (medium): SKILL.md's data-use sentence now covers only the zero-price lanes `free-lanes.md` asks about.
- Opus D8-4 (low): SKILL.md's opening line names the review and execute lanes and each role's order.

Left for a later loop: moving Step 1.6, 2.1 and 2.7 detail out of SKILL.md (referee-one D5-1, Opus D5-1, D1-1),
eval fixtures and graded outputs (referee-one D7-1, referee-two D7-1, Opus D7-1), and the remaining lows.
