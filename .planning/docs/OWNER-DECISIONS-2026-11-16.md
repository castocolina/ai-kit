# Owner decisions confirmed on 2026-11-16

On 2026-11-16 the owner read each provisional decision below in plain words and answered "accept all". This record
supersedes the "needs owner confirmation" and "needs awareness" flags in the named files for exactly these decisions.
A later plan may still change one of them through a dated amendment; until then a run treats them as decided and does
not stop to ask about them. Each item names the file that holds the full text.

## Phase 35 (`35-CONTEXT.md`)
- Tests for the cursor, codex and claude model formats, which have no provider prefix, use invented neutral model
  names (D-17).

## Phase 36 (`36-CONTEXT.md`, `36-SPEC.md`)
- Migrating the old reviewer roster deletes it after a value check and keeps no backup unless asked (D-10).
- jev scores every candidate model instead of picking one best; a stability rule for run-to-run variance belongs to the
  plan (D-07).
- The adapter's "no config, run spec-config" block is written in this phase, not in Phase 41 (D-03).
- A role whose lanes are all usage-limited may be written with a visible warning; the free-model group may include local
  models, labeled "local or hosted, unknown"; the free-model flag is the owner's opt-in to switch to the fallback lane on
  a quota stop (D-15 to D-19).
- A free-lane fallback comes from a different pool, and the wizard warns that free models of one provider share a pool
  (D-20 to D-22).
- The wizard shows each free model's data-use note and asks the owner to confirm sending project content (D-23).

## Phase 37 (`37-CONTEXT.md`)
- The runner owns every effort spelling (`--effort`); Python only passes the flag; this amends Phase 36's Python forms,
  which become transitional (D-01). This is about how effort is written for each CLI, not about choosing the effort a
  task needs, which Phase 42 owns.
- `--argv-file` lets a caller run a runtime the runner does not know, or a custom command, from a JSON file inside the
  working tree; the runner never reads a command from `config.toml` (D-05).
- The claude execute formula runs headless with permission checks off, like the other execute runtimes; the exact flag
  is picked by a recorded test in a scratch repo (D-09).
- herdr hosting is switched off only by `--host none` or `AIKIT_HOST=none`, with no config key (D-22 to D-29).
- A hosted lane's environment, which may hold API keys, goes through a mode-0600 file in a mode-0700 directory that the
  launcher deletes as its first step (D-25, shortened by Phase 38 D-31).

## Phase 38 (`38-CONTEXT.md`)
- A model alias declared by the owner's naming convention counts as behind the router, so a quota error on it waits and
  retries; a naming hint alone did not before (the router rule).
- The starter admission-phrase list (a summary that admits skipped work makes the result partial) and the default
  forbidden files (the three planning files GSD owns) decide a result and can be overridden in config.
- Hosted lanes cut their output files at twice the size cap; with hosting off, leftover tabs stay until `--sweep`; if the
  runner dies, a hosted lane runs to its end and its result is not recovered (D-25 to D-33).

## Phase 38.1 (`38.1-CONTEXT.md`, `38.1-RETRY-POLICY.md`)
- A new terminal class `bad_request` covers requests the server rejects (content filter, context too long, bad body).
- After the quick retries the hard tier waits 60 s, 300 s, then every 600 s up to 4 hours; an idle-killed lane retries
  the same way; `hard_every_s = 0` turns it off. A direct lane stops at once on a quota error.
- Free lanes (D-23 to D-27 and the todo `2026-11-16-opencode-free-models-open-checks.md`): the first retry time is the
  stated reset plus 120 s, with a 24-hour floor after a second failure in a row and a 24-hour cap on a stated reset
  above 24 hours; the block is keyed by provider pool, not by model.

## Phase 39 (`39-CONTEXT.md`)
- The after-approval pass where lens skills edit files is off by default (`edit_lens_pass`) and shows a diff for the
  owner to accept.

## Still open (not decided here)
- The five verification checks of the todo `2026-11-16-opencode-free-models-open-checks.md` (the reset rule, the exit
  code and event order in opencode 2.3.0, the headless error of a removed model, whether two free pools are shared, the
  missing official page). They are checks, not decisions.
- Whether the redacted transcript source of Phase 47.2 is on by default (marked "owner to confirm" there).
