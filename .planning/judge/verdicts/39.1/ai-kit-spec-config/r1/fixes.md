# Loop 39.1 round 1 fixes: ai-kit-spec-config

Five critical, important or high findings across the pool and the advisory lane (more than 3:
decide.py `next-round`). They are fixed before round 2, which judges the fixed skill.

- opencode:router-env/my-referee-one D8-1 (high): the catalog fetch now passes `--cwd "<project root>"`, and every fetch (catalog.md and cli-model-selection.md item 3) carries `AI_KIT_KEEP_MIGRATION_BACKUP=1` on Step 1.5's keep form. Files: `skills/ai-kit-spec-config/references/catalog.md`, `skills/ai-kit-spec-config/references/cli-model-selection.md`.
- opencode:router-env/my-referee-one D8-2 (high): after the owner's yes to the write-risk question, `--check-only` runs the preview snippet again and asks again when its list changed, before `probe-quota` runs. File: `skills/ai-kit-spec-config/references/check-only.md`.
- opencode:router-env/my-referee-one D8-3 (high): after the trusting `trust-local` call, its printed lines are compared with the approved `--show` lines; a difference revokes the trust at once and asks again. File: `skills/ai-kit-spec-config/SKILL.md`.
- opencode:router-env/my-referee-one D8-4 (high): the migrate-only answer and the `--check-only` raw read now say that an old roster with a lane naming a removed runtime is never migrated by a read, and offer the full setup to re-save those lanes. Files: `skills/ai-kit-spec-config/SKILL.md`, `skills/ai-kit-spec-config/references/check-only.md`.
- opencode:router-env/my-referee-three D8-1 (high, advisory lane): Step 4 checks the `render-toml` exit status first and runs `config-status` only after a confirmed write. File: `skills/ai-kit-spec-config/SKILL.md`.
