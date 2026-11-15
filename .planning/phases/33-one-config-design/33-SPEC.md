# Phase 33: One config design — Specification

**Created:** 2026-11-13 · **Rewritten:** 2026-11-14 (owner decisions; supersedes the 2026-11-13 agent draft)
**Ambiguity score:** 0.12 (gate: ≤ 0.20)
**Requirements:** 11 locked

## Goal

ai-kit keeps its settings in one neutral `config.toml` per layer (project `.aikit/config.toml`, user
`${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`), with one table per concern and entries structured by role, never
a file named after one skill that holds other skills' settings. The reviewer roster leaves `review-spec.toml` and the
runner's retry tuning leaves GSD's `config.json` and ai-kit's `cross-ai.json`, each migrating on its own with nothing
lost. ai-kit writes no key into another tool's schema and runs in a project without GSD. Every config write is atomic
and keeps comments, formatting and unrelated entries, and the design names the places Phases 34, 35, 36, 38.1 and 49
fill.

## Background

Requirements CFG-01..CFG-06 (REQUIREMENTS.md "One config design"). Skills a later phase removes or replaces
(`ai-kit-commit-fold`, the seven `ai-kit-project-rules-*`) are never judged (rails, Per phase end 0).

**The owner's decisions (2026-11-14, highest priority; they replace the 2026-11-13 agent draft, whose "one file per
concern" choice, `lanes.toml` and `.aikit/cross-ai.json` were never approved):**

- A file named after one skill (`review-spec.toml`) must not hold other commands' settings. Either one file with a
  neutral name (`config.toml`, `settings.toml`) whose entries are well structured, or one file per skill. The owner
  asked whether `./.aikit/` and the user directory should hold several configs or one with everything.
- The entries today are not well structured: spec-config was meant to build a catalog of every available model
  (models.dev and Artificial Analysis, the LM Arena leaderboard as the alternative), classify the models, and then
  propose the coding and review sets for the user to confirm; instead everything is labelled "reviews".
- `workflow.cross_ai_retry` was never requested: ai-kit must not add keys to a third-party schema, where they can be
  lost, and ai-kit must run in a project without GSD, so without `.planning/`.

**Settled for this spec** (the owner's rule: their words, then the 2026-11-07 transcript, then jev, then ask on low
confidence): one neutral `config.toml` per layer with one table per concern (jev, TypeSafe, choice 0.91; matches the
owner's "one file with a neutral name, well structured"), the user layer stays in the existing XDG directory
`~/.config/ai-kit` rather than a new `~/.aikit` (jev, TypeSafe, choice 0.82; the status line, consent and trust files
already live there). The owner was told both answers before this spec was written.

Live facts checked for this spec (2026-11-13 at `bb34055`, re-checked 2026-11-14; full table with `file:line` cites in
`tmp/auto/33-inventory.md`, to be committed as the R1 record):

- **Twelve ai-kit-owned settings locations** (9 files, 3 directories), plus settings that live only in the
  environment:
  - reviewer roster `.aikit/review-spec.toml` (project, `cfg_local_path`) and
    `${XDG_CONFIG_HOME:-~/.config}/ai-kit/review-spec.toml` (user, `cfg_global_path`), TOML: top `strategy`,
    `[policy]` (3 keys), `[[reviewers]]` (13 keys), 2 legacy keys loaded in memory only; both exist on this machine;
  - trust records `review-spec-trust/<sha256(realpath NUL content-sha)>.json` (user), pinned to the project file's
    realpath and the sha256 of its raw bytes, so any byte change needs a new trust (`trust.py`, `config_io.py:406-414`);
  - runner retry `cross-ai.json` key `cross_ai_retry` (user, JSON, 5 keys) and the error overlay
    `cross-ai-errors.json` (user, JSON array); neither exists on this machine; nothing writes them;
  - status line `claude-statusline.toml` and `cursor-statusline.toml` (user, TOML) and the `segments/`,
    `segments-cursor/` drop-in directories, written by the setup wizard;
  - `secrets.env` (user, 3 key names); `jev-consent.json` (user, per-backend `host`, `granted`);
  - unit-flow `.aikit/flow.json` (project main worktree, consent mixed with `remote`, `targets`, `gates`);
  - the model catalog cache (`model-catalog.json`, machine-written, `_meta` reserved);
  - environment only: the jev on/off switch (`GSD_PATH_JEV=1`) and the Laya URL (`JEV_LAYA_URL`, `AI_KIT_LAYA_URL`,
    default `http://127.0.0.1:8010`).
- **The runner's retry cascade** (`resolveRetry`, `cross-ai.mjs:3208-3268`), per key, first valid source wins: GSD
  `workflow.cross_ai_retry` from the scoped `.planning[/$GSD_PROJECT][/workstreams/$GSD_WORKSTREAM]/config.json`
  files, then the user `cross-ai.json`, then the rendered `CONFIG.retry`, then `RETRY_DEFAULTS`. `gsd-tools config-set`
  refuses `workflow.cross_ai_retry` ("Unknown config key"), so the block is hand-edited; gsd-core warns only on
  unknown top-level keys, so it loads silently. `workflow.cross_ai_timeout` is a real GSD key and stays GSD's.
- **The runner is a single node `.mjs` with node built-ins only**: it parses JSON and has no TOML parser.
- **Writers today**: the roster is written only by `render-toml` (`cfg_render_toml`, a full rewrite that drops the
  user's comments, then the atomic `cache_write_text`). The status-line writers patch TOML surgically
  (`write_toml_preserving`); the config doctor keeps comments in Codex TOML and opencode JSONC
  (`write_toml_region_replace`, `set_jsonc_value`); `_recover_incompatible_config` (`tools/setup.py:3496`)
  overwrites the live status-line file with `shutil.copyfile`, which is not atomic.
- **Four resolvers for the user config dir** differ (`cfg_config_base`, the runner's `aiKitConfigDir`,
  `common_config.py:273`, `setup.py:122`, `jev_review._config_dir`), and `local_secrets.secrets_env_path` ignores
  `XDG_CONFIG_HOME`.
- **Callers of the roster file**: `cfg_resolve` from `cli.py` (`_discovered_catalog_candidates`, `probe-quota`,
  `resolve-reviewers`, `resolve-timeout-tiers`) and `dispatch_injection.assemble_candidates`; `cfg_combine` from
  `trust-local`; `cfg_local_path`/`cfg_global_path` from `provider_check`; the write from `render-toml`; docs in
  `ai-kit-spec-config`, `ai-kit-spec-review`, `ai-kit-cross-ai`, `ai-kit-gsd-curated-config`,
  `ai-kit-spec-execute-superpowers` and the README.
- **GSD coupling**: the runner reads `.planning/` config for retry and timeout; `cfg_*` and the spec skills already run
  without `.planning/` except where they call gsd-tools for GSD's own settings.
- Python is pinned to 3.12; `tomllib` reads TOML; no TOML writer library exists in the tree.

## Requirements

1. **The settings inventory is committed (CFG-01)**: a committed record lists every settings location ai-kit owns, every setting kept only in the environment, the settings ai-kit reads from another tool's file, and the state and cache locations it keeps, each with path, layer, format, key names, writer, readers, atomicity and comment preservation.
   - Current: the facts exist only in code and in the run's scratch inventory.
   - Target: one Markdown record under `docs/config/` holds the inventory and the R2 decision; every row cites `file:line`.
   - Acceptance: a unit test collects the settings file names from the path functions the code uses and fails when one is missing from the record.

2. **One neutral config file per layer (CFG-01, owner 2026-11-14)**: ai-kit's settings live in `config.toml` in each layer, project `.aikit/config.toml` over user `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` per key, with one table per concern; machine-written state stays in its own files.
   - Current: settings are split across `review-spec.toml`, `cross-ai.json`, environment variables and GSD's `config.json`, under names tied to one skill.
   - Target: the record states the choice and its reasons; no new file or table is named after a skill or a host; the trust records, `jev-consent.json`, `secrets.env` (a credential), the model catalog cache, `.aikit/flow.json` (the unit flow's own, absorbed with commit-fold) and the status-line host files (the status-line tool's own, written by its wizard) each stay separate with their reason recorded.
   - Acceptance: the record's decision section names the two paths, the precedence rule and one assignment per inventory row; the R1 test also fails when a row has no assignment or a new path carries a skill or host name.

3. **Entries structured by role, with named places (CFG-05, owner 2026-11-14)**: `config.toml` has one table per concern: `[models]` (catalog sources and classification, filled by Phase 35), `[lanes]` with role-keyed lists `[[lanes.review]]` and `[[lanes.execute]]` (execute is the coding role; Phase 36 fills selection and escalation), `[runner]` with `[runner.retry]` (R7; Phase 38.1 sets the defaults), `[jev]` (Phase 34's Laya URL and on/off knob) and `[hooks]` (Phase 49's switches).
   - Current: every roster entry is a `[[reviewers]]` row, even where the intent is coding; the later keys have no home.
   - Target: the record documents each table, its keys and the phase that fills it; the reader accepts a table or key it does not know and keeps it through a write; a review lane and an execute lane are distinct entries, never one "reviewer" row reused for both.
   - Acceptance: a unit test reads a config with an unknown table and key (no error, values ignored), rewrites one known key and finds the unknown table byte-equal; a test loads one review and one execute lane and gets each under its role.

4. **The roster migrates on the first run (CFG-02)**: a project with an old `review-spec.toml`, local, global or both, is migrated into the matching layer's `config.toml` the first time an ai-kit command reads the roster, with nothing lost, and later runs do not migrate again.
   - Current: only `review-spec.toml` is read.
   - Target: each `[[reviewers]]` entry becomes a `[[lanes.review]]` entry with every key and value kept, `strategy` and `[policy]` move under `[lanes]`, comments and legacy fields are kept; the old file's full text stays recoverable; a one-line notice names both paths; a second run changes nothing; when both an old and a new roster exist the new one wins and the old one is reported, never merged again.
   - Acceptance: tests in a scratch home cover local only, global only, both, a `local-only` strategy, a file with comments and legacy fields, a second run (no byte change) and old-and-new present; parsed values of old and new are equal in each case.

5. **Trust survives migration and covers only command-bearing lanes**: a project roster that was trusted before migration is trusted after it with no new trust step, an untrusted one stays untrusted, and editing an unrelated table of `config.toml` does not drop trust.
   - Current: trust is pinned to the realpath and every byte of `.aikit/review-spec.toml`.
   - Target: trust pins the project file's realpath and a canonical digest of its command-bearing lane entries; migration re-keys a valid trust to that digest or leaves the roster untrusted; changing a command entry needs a new trust; `trust-local` and `provider_check` work on the new file.
   - Acceptance: tests migrate a trusted and an untrusted roster holding a custom `command` entry (the trusted one's entry resolves, the untrusted one's is ignored), edit `[runner.retry]` and keep trust, and edit the command and lose it.

6. **Every caller reads the new config (CFG-02)**: every reader and writer of the roster uses `config.toml`, and only the migration code still names `review-spec.toml`.
   - Current: the callers listed in Background read `review-spec.toml`; `render-toml` writes it.
   - Target: `cfg_resolve`, `cfg_combine`, `provider_check`, `trust-local`, `assemble_candidates`, `quota` and the writer use the new paths and tables; docs name the new config and mention the old name only as a migration source.
   - Acceptance: a unit test fails when runtime code outside the migration module or a doc outside a migration note names `review-spec.toml`; the existing roster tests pass against the new paths.

7. **The runner reads its retry tuning from ai-kit's config (CFG-03)**: the runner takes `[runner.retry]` keys from the project `config.toml`, then the user `config.toml`, then `CONFIG.retry`, then its defaults, per key with today's validation; a GSD `workflow.cross_ai_retry` block and the user `cross-ai.json` are migrated once and not read again.
   - Current: the GSD block is the runner's first source and the user `cross-ai.json` its second; the runner cannot read TOML.
   - Target: the runner gains a small reader for the TOML subset its tables use (tables, strings, integers, floats, booleans, arrays of numbers), node built-ins only, failing closed with a one-line notice on anything outside the subset; the GSD block's values land in the project `config.toml` (a workstream's or project's own block under `[runner.retry.scopes.<name>]`, read before the top level for the active scope) and the block is removed from the GSD file by an atomic write that keeps every other byte; the user `cross-ai.json` values land in the user `config.toml`; a block re-added later is ignored with a notice naming its file; `workflow.cross_ai_timeout` stays a GSD key read as today.
   - Acceptance: runner self-test cases cover migration from a project and a workstream GSD config, the user JSON migration, a re-added block (ignored, notice printed), a second run (no write), per-key precedence across the sources, an invalid key falling to the next source and a value outside the subset (notice, defaults used); the GSD file keeps every other byte.

8. **No ai-kit key in another tool's schema; ai-kit runs without GSD (CFG-06, owner 2026-11-14)**: ai-kit never writes a key that is not part of the other tool's own schema into that tool's config (GSD, Claude Code, opencode, Codex, Cursor, pi, Copilot), and every ai-kit skill CLI and the runner work in a repository that has no `.planning/`.
   - Current: the retry block sits in GSD's `config.json`; the runner looks for `.planning/` to find its settings.
   - Target: every ai-kit setting lives in `config.toml` or a recorded ai-kit state file; writes into another tool's config are limited to that tool's documented keys (GSD keys go through `gsd-tools config-set`, which rejects unknown keys); with no `.planning/` the spec skills, the runner and spec-config read and write only ai-kit's files and say nothing about GSD unless asked for GSD settings.
   - Acceptance: a test runs the roster resolve, the runner's retry resolution and spec-config's check-only path in a scratch repository without `.planning/` and finds no error and no `.planning/` created; a test fails when ai-kit code writes `cross_ai_retry` or another key outside gsd-core's key list into a GSD config.

9. **Every config write is atomic and lossless (CFG-04)**: every write ai-kit makes to its own config files and the GSD block removal goes through a temp file and an atomic rename, and keeps comments, formatting and unrelated entries.
   - Current: the roster writer drops comments; `_recover_incompatible_config` overwrites the live status-line file non-atomically.
   - Target: the new config's writer and both migrations change only the lines they own; the status-line recovery publishes through a temp file and `os.replace` after its `.bak` copy.
   - Acceptance: per writer, a test writes one key into a file holding comments, unusual spacing and an unknown table and asserts the byte diff covers only the written key's lines; a test interrupts each writer before the rename and finds the old file unchanged; a test asserts the recovery path never writes the live file in place.

10. **One resolver rule for the user config dir**: every ai-kit reader of a file in the inventory resolves `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit` by one rule: an absolute `XDG_CONFIG_HOME` is used, a relative one is ignored, and no absolute home is an error.
    - Current: four resolvers differ, and `local_secrets` ignores `XDG_CONFIG_HOME`.
    - Target: `config_io`, `local_secrets`, `jev_review`, the runner's `aiKitConfigDir` and the status-line resolvers follow the rule; copies that cannot share code carry a parity test.
    - Acceptance: a parity test runs each resolver on the same cases (absolute, relative and empty `XDG_CONFIG_HOME`; no home) and asserts the same result; `load_secret` and `jev_review` read the same `secrets.env` with `XDG_CONFIG_HOME` set.

11. **Docs and the judge bar (JDG-04)**: `ai-kit-spec-config`'s SKILL.md and a new README "ai-kit configuration" section describe `config.toml`, its tables, layers, the migration and the record; every SKILL.md this phase materially changes meets the judge bar with the judges referee-one and referee-two (referee-three replaces one that fails; one usable referee is accepted with the reason recorded; never native opus).
    - Current: spec-config's SKILL.md describes `review-spec.toml`; the README has no general config section.
    - Target: the text is updated; loop `33` judges exactly the materially changed SKILL.md files, never `ai-kit-commit-fold` or a project-rules skill.
    - Acceptance: 33-VERIFICATION.md lists each changed SKILL.md with its loop `33` result: no critical or high finding or grade B or better, and no regression beyond judge variation; `python3 tools/judge_loop.py check .planning/judge` exits 0.

## Boundaries

**In scope:**
- The committed inventory and decision record with its fitness test (R1, R2).
- `config.toml` per layer, its role-keyed tables, reader and comment-preserving atomic writer; the roster migration
  with trust re-keyed; every roster caller and doc moved (R3-R6).
- The runner's TOML-subset reader, retry sources and the one-time GSD block and user JSON migrations (R7).
- The no-foreign-key rule and the no-GSD run (R8); atomic lossless writes (R9); one resolver rule (R10); docs and
  loop `33` (R11).

**Out of scope:**
- Moving the status-line files, `jev-consent.json`, the trust records, `secrets.env`, the catalog cache or
  `.aikit/flow.json` into `config.toml` (R2 records why).
- Phase 34's jev keys, Phase 35's catalog build and classification, Phase 36's lane selection, ranking and escalation,
  Phase 38.1's retry policy values and Phase 49's hook switches: this phase gives each a documented table only (R3).
- `workflow.cross_ai_timeout` and every other real GSD key; GSD's own schema.
- Bringing `ai-kit-spec-review` or `ai-kit-cross-ai` to the judge bar (Phases 37-40).
- The 2026-11-13 agent draft's plans 33-01..33-11, research and pattern map: superseded by this spec, replanned
  from it.

## Constraints

- Runtime code stays stdlib-only; the runner stays node built-ins only; no new dependency (AGENTS.md); the TOML
  writer and the runner's reader follow the hand-rolled JSONC scanner precedent.
- Every write is atomic (`tempfile.mkstemp()` + `os.replace()`, the runner's temp + rename) and reuses the existing
  helpers where they fit.
- A broken `config.toml` stops the CLIs loudly (exit 2, as `ConfigError` does today), never silently disables review.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, read no `.planning/` path and stay flat under
  `tests/test_*.py` in the runner's groups; the rendered runner copy stays a pristine render (`make check-dogfood`).
- Plans are executable by a haiku executor: exact paths, small tasks, no design decision left open.
- English only; no machine-specific absolute path in source, tests or docs.

## Acceptance Criteria

- [ ] The inventory and decision record is committed; its test fails when a settings file name, an assignment or a neutral-name check is missing (R1, R2).
- [ ] A config with an unknown table reads without error and keeps it through a write; review and execute lanes load under their roles (R3).
- [ ] Local, global, both, `local-only`, commented and legacy roster files migrate into `[[lanes.review]]` with equal values; a second run changes no byte; old-and-new present keeps the new one (R4).
- [ ] Trust carries through migration, survives an unrelated edit and drops on a command edit; an untrusted roster stays untrusted (R5).
- [ ] No runtime code outside the migration module and no doc outside a migration note names `review-spec.toml` (R6).
- [ ] Runner self-test cases cover the GSD block and user JSON migrations, block removal with other bytes kept, a re-added block, no write on a second run, per-key precedence and an out-of-subset value (R7).
- [ ] The no-`.planning/` runs pass and no foreign key is written into a GSD config (R8).
- [ ] Each writer's test shows a diff limited to the written key; an interrupted write leaves the old file; the status-line recovery writes no live file in place (R9).
- [ ] The resolver parity test passes; both secrets readers read one file (R10).
- [ ] 33-VERIFICATION.md lists each changed SKILL.md with its loop `33` bar result and judges no removed skill (R11).
- [ ] `make test` passes.

## Edge Coverage

**Coverage:** 53/53 applicable edges resolved · 0 unresolved (53 engine rows from `edge_floor.py floor`, 0
unclassified)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | Two path functions that return the same file count once; the record lists each path once with every reader |
| empty | R1 | ✅ covered | A location that does not exist on a machine is still listed (the record is about code paths, not one machine) |
| encoding | R1 | 🧪 backstop | File names are ASCII; the test compares exact strings |
| ordering | R1 | ✅ covered | The record lists rows by layer, then path; the test ignores order |
| concurrency | R1 | 🧪 backstop | The record is a static document; the test only reads |
| adjacency | R2 | ✅ covered | Project and user `config.toml` holding the same key: the project value wins for that key only; other keys still come from the user file |
| empty | R2 | ✅ covered | No `config.toml` in either layer: built-in defaults apply, nothing is written until a command saves a value |
| encoding | R2 | ✅ covered | UTF-8 TOML read by `tomllib`; a decode error is a `ConfigError` (exit 2) naming the file |
| ordering | R2 | ✅ covered | Precedence is fixed: project, then user, then defaults, per key |
| concurrency | R2 | ✅ covered | Writers publish by temp file and rename; a reader sees the old or the new file, never a mix |
| adjacency | R3 | ✅ covered | A lane listed under both `review` and `execute` is two entries with their own keys; changing one never changes the other |
| empty | R3 | ✅ covered | A missing table reads as empty; an empty `[[lanes.execute]]` list means no executor lanes configured |
| ordering | R3 | ✅ covered | Lane order inside a role is the priority order, kept on write |
| idempotency | R3 | ✅ covered | Writing the same value twice leaves the file byte-equal |
| concurrency | R3 | 🧪 backstop | Same atomic writer as R2 |
| adjacency | R4 | ✅ covered | Old and new roster in one layer: the new one wins, the old one is reported once per run, never merged |
| empty | R4 | ✅ covered | An empty old roster migrates to an empty `[lanes]` table and the notice still names both paths |
| encoding | R4 | ✅ covered | Comments and values are copied as UTF-8 text; parsed values compare equal |
| ordering | R4 | ✅ covered | Reviewer order is kept as review-lane order |
| concurrency | R4 | ✅ covered | Migration writes the new file, re-reads it, then retires the old one; an interruption leaves every value in one of the two files |
| adjacency | R5 | ✅ covered | Editing a non-lane table keeps trust; editing any byte of a command-bearing lane entry drops it |
| empty | R5 | ✅ covered | A roster with no command-bearing lane needs no trust and none is recorded |
| ordering | R5 | ✅ covered | The canonical digest sorts entries by role and position, so reformatting whitespace keeps trust |
| idempotency | R5 | ✅ covered | Re-keying an already re-keyed trust changes nothing |
| concurrency | R5 | 🧪 backstop | Trust records are written atomically as today |
| adjacency | R6 | ✅ covered | A doc line that names `review-spec.toml` as the migration source is allowed; any other mention fails the test |
| empty | R6 | 🧪 backstop | No caller runs without a roster path; the existing tests cover the no-config path |
| encoding | R6 | 🧪 backstop | ASCII path strings |
| ordering | R6 | 🧪 backstop | Caller order does not matter |
| adjacency | R7 | ✅ covered | A key present in the project and user files: the project value wins; a scope block wins over the top level for the active scope only |
| empty | R7 | ✅ covered | No `[runner.retry]` anywhere: `CONFIG.retry`, then defaults, as today |
| encoding | R7 | ✅ covered | The subset reader accepts UTF-8 and the listed value types; anything else is a notice and that file is skipped |
| ordering | R7 | ✅ covered | Per key: project, user, `CONFIG.retry`, defaults |
| idempotency | R7 | ✅ covered | A second run finds no GSD block and no user JSON to migrate and writes nothing |
| concurrency | R7 | ✅ covered | Two runners starting together: the migration takes the runner's existing lock or loses to a newer file and re-reads; the GSD file is rewritten by temp and rename |
| adjacency | R8 | ✅ covered | A GSD key ai-kit legitimately sets (through `config-set`) is allowed; any key gsd-core does not list is refused |
| empty | R8 | ✅ covered | A repository with no `.planning/` at all: every listed command runs and creates no `.planning/` |
| ordering | R8 | 🧪 backstop | No ordering involved |
| idempotency | R8 | ✅ covered | Repeated no-GSD runs leave the repository unchanged |
| concurrency | R8 | 🧪 backstop | No shared state beyond R2's files |
| adjacency | R9 | ✅ covered | The written key's line and its neighbours: only the key's own lines change |
| empty | R9 | ✅ covered | Writing into a missing file creates it with only the written table |
| ordering | R9 | ✅ covered | Unrelated tables keep their position |
| concurrency | R9 | ✅ covered | Interrupted before the rename: the old file is unchanged (test) |
| adjacency | R10 | ✅ covered | `XDG_CONFIG_HOME` equal to `$HOME/.config` gives the same directory as unset |
| empty | R10 | ✅ covered | Empty `XDG_CONFIG_HOME` is treated as unset |
| ordering | R10 | 🧪 backstop | One rule, no ordering |
| concurrency | R10 | 🧪 backstop | Pure path resolution |
| adjacency | R11 | ✅ covered | A SKILL.md that only renames a path is recorded as not materially changed (listed, not judged) |
| empty | R11 | ✅ covered | If no SKILL.md is materially changed beyond spec-config, loop `33` judges spec-config alone |
| encoding | R11 | 🧪 backstop | Docs are UTF-8 Markdown |
| ordering | R11 | 🧪 backstop | Judge rows in loop order |
| concurrency | R11 | 🧪 backstop | Judges run through the existing loop tool |

## Prohibitions (must-NOT)

**Coverage:** 6/6 applicable prohibitions resolved · 0 unresolved (canon: config-file safety in general, path
traversal and symlink confinement are owned by `/gsd-secure-phase`; the rows below are this phase's own product rules)

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT copy a secret value (an API key or token from the environment or `secrets.env`) into any config file or the record | R1, R2, R4 | resolved | verification: test — a migration and record test seeds a key in the environment and `secrets.env` and asserts its value appears in no written file |
| MUST NOT make an untrusted project roster's command-bearing entry runnable through migration | R5 | resolved | verification: test — the R5 untrusted case |
| MUST NOT delete or overwrite an old roster file's content before the new config holding all its values is written and re-read | R4 | resolved | verification: test — the R4 tests interrupt migration after the new write and before cleanup and find every value in one of the two files |
| MUST NOT write a key outside another tool's own schema into that tool's config | R8 | resolved | verification: test — the R8 foreign-key test |
| MUST NOT require `.planning/` or GSD for an ai-kit skill or the runner to read its settings | R8 | resolved | verification: test — the R8 no-`.planning/` runs |
| MUST NOT judge `ai-kit-commit-fold`, a project-rules skill, or a skill whose SKILL.md this phase leaves materially unchanged | R11 | resolved | verification: judgment — the verifier compares loop `33` rows with the changed SKILL.md files and the rails' removal list |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Owner decisions of 2026-11-14 fix the layout, names and the foreign-schema rule |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | What moves now is fixed; later phases' tables named only |
| Constraint Clarity | 0.86  | 0.65 | ✓      | stdlib and node built-ins, atomic helpers, scratch HOME, haiku-executable plans |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | Eleven pass/fail checks, each tied to a test, the runner self-test or a command |
| **Ambiguity**      | 0.12  | ≤0.20| ✓      | 1 − (0.35×0.90 + 0.25×0.88 + 0.20×0.86 + 0.20×0.84) |

## Interview Log

Owner-led rewrite (2026-11-14) of the 2026-11-13 auto draft. Order of authority: the owner's words of 2026-11-14, then
the 2026-11-07 transcript, then jev, then the owner on low confidence. Summaries only, advisory. Rule: `mvp-mode`
inactive, so the best design wins over the smallest diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | Which settings does ai-kit keep, where, written how? | none | Live inventory from the code: 12 locations, env-only jev keys, the runner's four-source retry cascade, four user-dir resolvers (Background, R1, R10) |
| 1 | Owner | One neutral file or one file per skill; one directory with several configs or one with everything? | choice 0.91 (typesafe: one config.toml per layer, a table per concern, state files apart) | One `config.toml` per layer, tables by concern, machine-written state apart (R2); the owner's "neutral name, well structured" |
| 1 | Owner | `./.aikit/` and `~/.aikit`, or the existing XDG directory? | choice 0.82 (typesafe: keep ~/.config/ai-kit) | Project `.aikit/`, user `~/.config/ai-kit` (R2, R10) |
| 1 | Owner | How are entries structured so coding is not labelled review? | none | Role-keyed `[[lanes.review]]` and `[[lanes.execute]]`; the catalog flow is Phase 35-36 work (R3, ROADMAP amendments) |
| 1 | Owner | Where does the retry tuning live, and may ai-kit add keys to GSD's config? | none | In ai-kit's `config.toml` `[runner.retry]`; the GSD block is migrated out and removed; no foreign keys; ai-kit runs without `.planning/` (R7, R8) |
| 1 | Failure Analyst | One shared file means unrelated edits touch the trusted file; does trust break? | none | Trust pins only the command-bearing lane entries (R5) |
| 1 | Failure Analyst | What would make migration lose or widen something? | none | Trust carried, never widened (R5); old text recoverable and never removed before the new file is re-read (R4); secrets never copied (prohibitions) |

---

*Phase: 33-one-config-design*
*Spec rewritten: 2026-11-14*
