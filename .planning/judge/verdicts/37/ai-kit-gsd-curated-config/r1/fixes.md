# Loop 37 round 1 fixes: ai-kit-gsd-curated-config

Fix rule (AGENTS.md): 1 critical, important or high finding across both judges, fixed in the skill's own files; no further round. The skill's digest is stale by design until its next loop.

- D8-2 (referee-one, high): the `.new` merge check now has a pass criterion: the active runner's `template=` header names the bundled template and the `--print-argv` line names the approved runtime, an installed binary (not `MISSING`), the approved model and an argv (not `NO MODEL`); the exit code proves nothing; on a mismatch `.new` stays, no model is dispatched and the line is reported. File: `skills/ai-kit-gsd-curated-config/references/runner.md`.
