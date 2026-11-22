# Loop 38 round 1 fixes: ai-kit-gsd-curated-config

Fix rule (AGENTS.md): 3 critical, important or high findings across both judges, fixed in the
skill's own files with no further round; the skill's digest is stale by design until its next loop.

- referee-one D8-1 (SKILL.md:168, high): step 4 now says `apply` recomputes its writes from the live config (apply.py `_prepare_writes`: `read_live_config` then `diff_entries`) without comparing them to the approved preview, so the dry run is run again right before the real apply and any changed row goes back to the user; it names the remaining concurrent-edit window. Binding apply to the preview in code is not done here. File: skills/ai-kit-gsd-curated-config/SKILL.md.
- referee-one D8-3 (SKILL.md:354, high): tuning questions now route to `gsd-config --advanced` and integration questions to `gsd-config --integrations`, as the project-local `.claude/commands/gsd-config.md` defines. File: skills/ai-kit-gsd-curated-config/SKILL.md.
- referee-one D8-4 (references/runner.md:32 and SKILL.md:234-236, high): `--codex-sandbox workspace-write` is now described as Codex's `workspace-write` sandbox, not a fixed path allowlist: the project dir plus `/tmp` and `$TMPDIR` by default, with the owner's Codex config able to add or exclude writable roots (flagged not verified here), and the agent checks the effective roots before promising a boundary. Files: skills/ai-kit-gsd-curated-config/references/runner.md, skills/ai-kit-gsd-curated-config/SKILL.md.
