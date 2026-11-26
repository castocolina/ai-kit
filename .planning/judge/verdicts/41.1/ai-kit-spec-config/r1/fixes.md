# Loop 41.1 round 1 fixes: ai-kit-spec-config

Decide row: `fix` (2 critical, important or high findings: referee-one 2, referee-three 0). With 3 or fewer such findings the fix needs no further judge round, so the skill's digest is stale by design until its next loop; the round's validated score already met the bar (worst B 86.4, loop 41 base 88.8, no regression).

Both findings were checked before the fix, neither refuted:
- D8-1: `cfg_config_base` in `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` ignores a relative `XDG_CONFIG_HOME` (its docstring says so), while check-only.md gave the shell form `${XDG_CONFIG_HOME:-~/.config}`.
- D8-2: `render-toml --json-config` on a codex review lane carrying `servce_tier = "fast"` (scratch HOME, stdout only) printed the entry with `servce_tier = "fast"` and `render-toml exit 0`.

- referee-one D8-1 (high, `skills/ai-kit-spec-config/references/check-only.md:10`): the `--global` raw read now names the user file by the "Layers" path rule, the path the quota preflight resolves (`$XDG_CONFIG_HOME/ai-kit/config.toml` only when that value is absolute, else `~/.config/ai-kit/config.toml`), with the relative-value example; the "Layers" line of config-file.md states the same rule instead of the shell default form. Files: references/check-only.md, references/config-file.md.
- referee-one D8-2 (high, `skills/ai-kit-spec-config/SKILL.md:227`): Step 3 no longer says `render-toml` rejects anything outside the field list; it says the writer keeps an unknown key (a misspelled knob still exits 0) and points to "Lane entry fields", which now lists the flat per-lane `timeout_tiers` and a custom entry's template fields and holds the key check: every entry's keys are checked against that list before `render-toml` runs. Files: SKILL.md, references/config-file.md.

Tests before commit (text-only change, no test edited): `bash tmp/judge-41.1/fix_tests.sh`: 18/18 modules passed.
