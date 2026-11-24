# Loop 39.1.1 round 3 fixes: ai-kit-spec-config

Round 3 left no critical, important or high finding (referee-two A 90.4, advisory referee-three B 88.0; referee-one's
lane failed on a blocked route). Round 3 is the loop's last round, so no judge round follows: two small, truthful
medium fixes that both remaining judges or one judge's loading note asked for are made here, and the skill's digest is
stale by design until its next loop. No code changed.

- opencode:router-env/my-referee-two D8-1 and opencode:router-env/my-referee-three D8-1 (medium): the sentence after
  the pinned pair-rule paragraph names the source of the four claude aliases: the `native_selectors` of the claude row
  of `RUNTIMES` in the review skill's `ai_kit_spec/detection.py` (checked; `routing.py` runs only those natively), not
  Claude Code's whole alias list, and Step 1's `detect-runtimes` prints them as `clis.claude.aliases` for an installed
  claude (`detection.claude_runtime_fields`); Step 2.7's claude case points the alias pick at that list (also
  referee-three D8-2, low). File: `skills/ai-kit-spec-config/SKILL.md`.
- opencode:router-env/my-referee-two D5-1 (medium): catalog.md's optional-sources and corrections sections each open
  with the condition to skip them on a plain setup. File: `skills/ai-kit-spec-config/references/catalog.md`.

Two corrections to earlier rounds of this loop, made in the same commit:

- Round 2 had changed Step 2.6 to leave `strength` unasked unless the owner raises it (referee-three r2 D6-1, low);
  that removed a question the wizard offers, so the round 1 form is restored: one optional `strength` offer per run,
  default none, saying it is informational. Files: SKILL.md, `references/wizard-flow.md`.
- The round 1 catalog.md sentence "leave `--catalog-path` out at Step 3" is now checked by a recorded scratch-HOME run
  (`tmp/judge-39.1.1/verify_no_catalog.sh`: a session-default-only JSON, no catalog file, no `--catalog-path`:
  `render-toml exit 0`, empty stderr, the lane and its order written); no text change was needed.

Left for a later loop (larger than a text fix): eval fixture files for the existing-roster, pending-migration and
global-write cases (referee-three D7-1, referee-two D7-1), and moving Step 2.7/2.8 detail out of SKILL.md
(referee-three D5-1). Referee-two D6-1 (low) asks for a read-only probe-key subcommand in place of check-only.md's snippet;
that is a code change: ROADMAP backlog 999.29, and check-only.md now states the current limit (the snippet imports
private helpers, so a rename breaks it; its nonzero exit is already handled). Files:
`skills/ai-kit-spec-config/references/check-only.md`, `.planning/ROADMAP.md`.
