# ai-kit configuration design

This record is the inventory and decision for SPEC R1 and R2 (phase 33, plan 11). It lists every
settings location ai-kit owns, every setting kept only in the environment, the settings ai-kit reads
from or writes to another tool's file, and the state and cache locations. Each row names its path,
layer, format, key names, writer, readers, atomicity and comment handling, with a `file:line` cite.
Cites were refreshed against the tree on 2026-11-15. The record names key names only, never a value.

## Decision

ai-kit keeps its settings in one neutral file per layer:

- project: `.aikit/config.toml`
- user: `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`

Precedence is `per key: project, then user, then built-in defaults`. A key the project file sets
wins for that key only; every other key still comes from the user file, and a key neither file sets
comes from the built-in default.

Reasons:

- A file named after one skill cannot hold other skills' settings (owner decision, 2026-11-14). The
  reviewer roster, the runner's retry tuning and the jev settings are read by several skills, so one
  neutral file avoids copies and cross-references between skills.
- The user layer stays in the XDG folder that already holds ai-kit's status-line, consent and trust
  files, and that folder honours an absolute `XDG_CONFIG_HOME` (see Resolver rule).
- Settings group into tables by concern (see Tables). No file or table is named after a skill or a
  host.
- Machine-written state, credentials and another tool's own file stay in their own files. Each keeps
  its reason in Assignments.

## Tables

Phase 33 creates `[lanes]` and `[runner]`. The other tables are documented here with the phase that
fills each; the runner reads only `[runner]` and `[runner.retry*]` through its TOML-subset reader.

- `[lanes]`: `strategy` (`global-merge` by default, or `local-only`). The policy keys sit in
  `[lanes.policy]`: `mode` and `timeout_tiers`. A legacy flat `ladder` there loads as each role's
  order, filtered to that role's lanes, with a note, and the next write replaces it.
- `[lanes.policy.review]` and `[lanes.policy.execute]`: `ladder`, each role's priority order (lane
  keys, first available wins). A role with no lane gets no table; the project layer's role table
  replaces the user's for that role. `config-status` reports whether either layer holds a lane
  (`active`, `pending` or `none`) and writes nothing; `propose-lanes` ranks catalog models per
  purpose and writes nothing.
- `[[lanes.review]]`: one entry per review lane. Keys: `key`, `model`, `vendor`, `runtime`, `command`,
  `purpose`, `effort`, `effort_source`, `service_tier`, `task_affinity`, `context_limit`, `is_router`,
  `fallback_quota`, `escalate_runtime`, `escalate_model`, `usage_limited`, `usage_limit_note`, `pool`,
  the data-use record (`data_use`, `data_use_line`, `data_use_source`, `data_use_read`,
  `data_use_label`, `data_use_confirmed`), and flat extra keys. The escalation and usage-limit flags
  are written only when true and the data-use record only with the owner's yes; no run reads the
  flags yet. Legacy `cli` and `native_runtime` load in memory only, and `route` is refused on save.
- `[[lanes.execute]]`: one entry per execute (coding) lane, with the same entry keys. A lane is never
  shared between the two roles; the wizard writes only the lanes the owner chose for each role.
- `[runner]`: `migrated_from`, the list of legacy sources the runner has migrated (written by the
  runner's one-time migration). Phase 33.
- `[runner.retry]`: `base_s`, `factor`, `max_retries`, `session_resets`, `hard_waits_s` (default
  `[60, 300]`), `hard_every_s` (0 or 60..`capS`, default 600: the wait after the list until the
  4-hour cap; 0 stops at the list's end). Phase 38.1 sets the default values.
- `[runner.retry.scopes."<scope>"]`: the same six keys for one GSD scope. The scope is the config
  directory's path under `.planning/` with `/` separators, for example `"myproj"` or
  `"myproj/workstreams/ws1"`. The scope table wins over `[runner.retry]` for its own scope only.
- `[models]` (Phase 35, read by `models_config.read_models_settings`, written by `models-config`): `sources` (any of `models.dev`, `artificial-analysis`, `arena`; default all three), `[models.cache_days]` (`models_dev`, `artificial_analysis`, `arena`, whole days, default 7; host listings keep 30 days), `[[models.context]]` (`runtime`, `model`, `tokens`: a user-stated context window per (runtime, model)). Project over user per key: a project `[[models.context]]` array replaces the user array. The Artificial Analysis key stays in `secrets.env`. The review and execute dispatch read a matching `[[models.context]]` entry as the lane's known window before the catalog value; a prompt whose estimate exceeds it is refused before the spawn (exit 65).
- `[skills.roles]` (written only by `confirm-skill-role`, read by `skill_table.user_roles`): a map from a skill or MCP server name to one role of the closed list (`review_lens`, `edit_lens`, `ui_lens`, `code_index`, `decision_helper`, `host_control`, `skill_judge`); each entry is a sort the owner confirmed, labeled `user-stated`, and beats the seed file `skills/ai-kit-spec-review/references/skill-roles.json`. Project over user per name.
- `[review]`: `edit_lens_pass` (boolean, default false): after the reviewers approve, `edit-lens-pass` runs the present `edit_lens` skills on one execute lane whose `write` is `workspace` or `full` (at present only codex lanes report one) and shows the diff for the owner to accept or reject; an unattended run never enables it.
- `[jev]`: `laya_url` (string, any address; `""` means no Laya), `laya_version` (string, for a server
  that exposes no version) and `enabled` (bool). Read by jev-fast-decision through its parity-tested
  copy of the layered reader (`jev_table`, `jev_config.py:621`), project over user per key, with
  `JEV_LAYA_URL`/`AI_KIT_LAYA_URL` and `GSD_PATH_JEV` as session overrides; `jev_review.py config set`
  writes the user layer only (`config_set`, `jev_config.py:663`). Phase 34.
- `[hooks]`: hook switches. Phase 49. Not read in Phase 33.

`model-catalog.json` (schema 4): `facts.<name>` = {value, label, source, fetched_at[, confidence]}, `identity`, `confirmed_fields`, and per runtime `ctx_window` (int), `context` (fact), `usability` {state, at, via, error}, `efforts`, `last_seen`.

The Python reader accepts a table or key it does not know and keeps it through a write. The runner's
subset reader (D-07) reads only `[runner]` and `[runner.retry*]` and skips every other table as opaque.
Inside the runner tables it takes only `key = value` lines with basic strings, integers, floats, booleans
and arrays of numbers or strings; anything else there (an inline table, a date, a nested array, a
multi-line string) skips the whole file (one notice, next source). Anywhere in the file it also skips the
file for a multi-line string outside `[lanes]` and `[[lanes.*]]` (inside them it is skipped until its
delimiter closes), an array of tables outside `[lanes]`, a `runner` key before the first table header, or a
line shaped like a table header it cannot name (a nested array element alone on its line counts). A `'''`
or `"""` inside a comment or a one-line string does not count.

## Roles

Each lane entry's `purpose` picks its role (D-24):

- `review`, or no `purpose`: `[[lanes.review]]`.
- `execute`: `[[lanes.execute]]`.
- `both`: one entry in each role.

Every key is kept as written, `purpose` included. Readers that still use the flat `reviewers` view
receive both roles' entries, one per `key`.

## Trust

trust covers the project file's command-bearing lane entries; every other table is ordinary settings.

- The trust record pins the realpath of `.aikit/config.toml` and a sha256 over the canonical JSON of
  its command-bearing lane entries (roles in sorted order, entries in file order, sorted keys).
  Editing another table, a comment or spacing keeps trust. Changing or adding a command-bearing entry
  needs a new trust. A project file with no command-bearing entry needs none.
- Override refinement: a project lane entry whose `key` matches a user command entry is pinned too,
  so the project file cannot replace a user command without a new trust.
- Trust records live in the user `config-trust/` folder. A repository cannot trust itself.
- The migration carries trust: a valid record in the old `review-spec-trust/` store is re-keyed to the
  new digest in `config-trust/` before the old file is retired.
- `trust-local` prints and records the canonical digest; `trust-local --revoke` revokes both the new
  and the old record.

## Resolver rule

One rule resolves the user config folder `${XDG_CONFIG_HOME:-~/.config}/ai-kit`:

1. An absolute `XDG_CONFIG_HOME`, with surrounding whitespace removed, gives `<that path>/ai-kit`.
2. An empty, whitespace-only or relative `XDG_CONFIG_HOME` is treated as unset (D-27).
3. Otherwise an absolute `HOME` gives `<HOME>/.config/ai-kit`.
4. Otherwise there is no user folder, and every reader treats the user layer as absent.

`HOME` comes from the environment only; no copy calls an ambient home lookup. The cache folders
resolve on their own rule (`cache.py:9-12`), which this rule does not cover.

Copies of the rule, one per code boundary that cannot share code (D-19):

- `config_io.cfg_config_base`: `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:267-280`
- `local_secrets._config_base` and `secrets_env_path`: `skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py:10-20`
- `jev_review._config_dir`: `skills/jev-fast-decision/scripts/jev_review.py:1212`
- `common_config.cfg_ai_kit_dir`: `tools/common_config.py:263-271`
- `setup.resolve_paths`: `tools/setup.py:103`
- the runner's `aiKitConfigDir`: `skills/ai-kit-spec-review/references/cross-ai.mjs:3373-3378`

`tests/test_config_dir_parity.py` runs every copy on the same cases: absolute, relative, empty and
whitespace `XDG_CONFIG_HOME`, and HOME unset, empty or relative.

## Assignments

Each inventory location has exactly one row. Rows are grouped by layer, then by path. The record's
tests read this table and fail when a location has no row, has two rows, or has an empty assignment.

| Location | Layer | Assignment | Reason |
| --- | --- | --- | --- |
| `.aikit/config.toml` | project | `config.toml`: `[lanes]`, `[runner]`, `[runner.retry]` | the project layer of ai-kit's one config file |
| `.aikit/flow.json` | project | separate: unit-flow settings and consent | the unit flow's own file, absorbed with commit-fold later |
| `.aikit/review-spec.toml` | project | migration source for `[lanes]` in `.aikit/config.toml`; deleted after the value check by default (a changed file stays under its name; a failed final removal leaves a `.retiring` copy to remove by hand), or renamed `.migrated` with `AI_KIT_KEEP_MIGRATION_BACKUP=1` | migrated on the first roster read |
| `.planning/config.json` | project, GSD's file | migration source for `workflow.cross_ai_retry` into `[runner.retry]`; `workflow.cross_ai_timeout` stays GSD's | another tool's schema (D-17); the runner migrates the legacy block once |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/claude-statusline.toml` | user | separate: status-line tool | written and patched by the status-line wizard and doctor |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cursor-statusline.toml` | user | separate: status-line tool | written and patched by the status-line wizard and doctor |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments` | user | separate: status-line providers (a folder) | the Claude providers folder the status-line wizard installs |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments-cursor` | user | separate: status-line providers (a folder) | the Cursor providers folder the status-line wizard installs |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config-trust` | user | separate: consent records | machine-written; a repository must not trust itself |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` | user | `config.toml`: `[lanes]`, `[runner]`, `[runner.retry]` | the user layer |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai-errors.json` | user | separate: data overlay | a JSON array the runner loads, not a setting |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json` | user | migration source for `[runner.retry]` in the user `config.toml`; renamed `cross-ai.json.migrated` | migrated once by the runner |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/jev-consent.json` | user | separate: consent | bound to a backend host |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/review-spec-trust` | user | migration source for `config-trust` | a trusted record is carried by the migration |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/review-spec.toml` | user | migration source for `[lanes]` in the user `config.toml`; deleted after the value check by default (a changed file stays under its name; a failed final removal leaves a `.retiring` copy to remove by hand), or renamed `.migrated` with `AI_KIT_KEEP_MIGRATION_BACKUP=1` | migrated on the first roster read |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/secrets.env` | user | separate: credential | never merged into a settings file |
| `${XDG_CACHE_HOME:-~/.cache}/ai-kit/spec/model-catalog.json` | cache | separate: cache | machine-written data, `_meta` reserved |

## Inventory

Settings locations ai-kit owns (section 1 of the scratch inventory, refreshed). Key names only.

| Location | Layer | Format | Key names | Writer | Readers | Atomic | Comments kept |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `.aikit/config.toml` | project | TOML | the tables in Tables | `_cmd_render_toml` (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:797`) through `cfg_render_lanes` (`config_io.py:909`) and `cfg_write_toml` (`config_io.py:941`); the migrations (`config_migrate.py:360`, `cross-ai.mjs:3827`) | `cfg_resolve` (`config_io.py:614`), `cfg_combine` (`config_io.py:682`), `resolveRetry` (`cross-ai.mjs:3516`); `jev_table` (`jev_config.py:621`) | yes: `toml_splice.publish` (`toml_splice.py:780`) | yes: a splice changes only the lines it owns |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` | user | TOML | the tables in Tables | the same writers, with the user target chosen by `cfg_migrate_target` (`config_io.py:512`); jev-fast-decision's `config_set` (`jev_config.py:663`) writes only `[jev]` | `cfg_global_path` (`config_io.py:291-293`), `resolveRetry` (`cross-ai.mjs:3528-3529`); `jev_table` (`jev_config.py:621`) | yes | yes |
| `.aikit/review-spec.toml` | project | TOML (old) | the old roster keys, copied under `[lanes]` | none after the migration | `legacy_path` (`config_migrate.py:42`), `migrate_layer` (`config_migrate.py:363`) | the old file is deleted after the value check by default (a changed file stays under its name; a failed final removal leaves a `.retiring` copy to remove by hand), or renamed to `.migrated` with the keep switch | only in the `.migrated` copy, when kept |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/review-spec.toml` | user | TOML (old) | the old roster keys, copied under `[lanes]` | none after the migration | `migrate_layer` (`config_migrate.py:363`) | deleted after the value check by default (a changed file stays under its name; a failed final removal leaves a `.retiring` copy to remove by hand), or renamed to `.migrated` with the keep switch | only in the `.migrated` copy, when kept |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config-trust/` | user | JSON, one file per trusted content | `path`, `sha256`, `trusted_at` | `record_trust` (`trust.py:49`) through `cache_write_json` (`cache.py:23`) | `is_trusted` (`trust.py:39`), `revoke_trust` (`trust.py:61`) | yes (`cache_write_bytes`) | n/a (generated) |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/review-spec-trust/` | user | JSON (old) | the old record keys | none after the migration | `legacy_trust_dir` (`config_migrate.py:47`), `revoke_legacy_trust` (`config_migrate.py:58`) | n/a | n/a |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/claude-statusline.toml` | user | TOML | `[segments]`, `[[line]]`, `[palette]`, `[ramp.*]`, `[git]`, `[external]` | `save_statusline_config` (`tools/setup.py:3098`) through `write_toml_preserving` (`tools/setup.py:818`); recovery `_recover_incompatible_config` (`tools/setup.py:3471`) | `cfg_load_toml` (`tools/common_config.py:288`) | yes: `os.replace` (`tools/setup.py:862`); recovery publishes by `os.replace` (`tools/setup.py:3512`) after a `.bak` copy (`tools/setup.py:3500`) | yes: surgical patches keep other bytes |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cursor-statusline.toml` | user | TOML | as the Claude file, plus `[cursor]` | the same writers with the Cursor host | `cfg_load_toml` (`tools/common_config.py:288`) | yes | yes |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments/` and `segments-cursor/` | user | executables with a `# ai-kit-segment:` header | header fields `line`, `id`, `timeout`, `ttl`, `position` | `install_example_segments` (`tools/setup.py:1143`) through `_atomic_write_executable` (`tools/setup.py:1126`) | `cfg_segments_dir` (`tools/common_config.py:509`) | yes | n/a |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai-errors.json` | user | JSON array of pattern rows | row fields checked by the runner | none: hand-edited | `loadOverlay` (`cross-ai.mjs:3380`, file at `cross-ai.mjs:3386`) | n/a | n/a |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json` | user | JSON (old) | `cross_ai_retry` | none after the migration | `migrateRetrySources` (`cross-ai.mjs:3977-3978`) | renamed to `cross-ai.json.migrated` | kept in the `.migrated` copy |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/secrets.env` | user | env-style `KEY=VALUE` lines | `ARTIFICIAL_ANALYSIS_API_KEY` (`cli.py:518`), `JEV_API_KEY`, `TYPESAFE_API_KEY` (`jev_review.py:979-983`) | none: hand-edited | `load_secret` (`local_secrets.py:23`), `_secrets_env_value` (`jev_review.py:869`) | n/a | n/a |
| `${XDG_CONFIG_HOME:-~/.config}/ai-kit/jev-consent.json` | user | JSON | per backend: `host`, `granted` | `write_consent` (`jev_review.py:1241`, temp file at `jev_learn.py:84`) | `read_consent` (`jev_review.py:1231`), `record_consent` (`jev_review.py:1279`) | yes (`mkstemp` and `os.replace`) | n/a |
| `.aikit/flow.json` | project (main worktree) | JSON | `schema`, `repo`, `consent`, `granted`, `remote`, `targets`, `gates` | `write_settings` (`flow_record.py:189`) through `_atomic_write_json` (`flow_record.py:112`) | `read_settings` (`flow_record.py:176`), `_settings_path` (`flow_record.py:172-173`) | yes | n/a |
| `${XDG_CACHE_HOME:-~/.cache}/ai-kit/spec/model-catalog.json` | cache | JSON | catalog entries keyed `provider/model`; `_meta` reserved | `cache_write_json` (`cache.py:23`) | `cache_catalog_path` (`model_catalog.py:54-55`) | yes | n/a |

Two notes: the consent and trust files each mix a consent record with settings in one case only
(`.aikit/flow.json` keeps `remote`, `targets` and `gates` beside the consent, which the unit flow owns);
and `secrets.env` holds credentials, so no settings file ever merges it.

## Environment-only settings

These settings have no file home, except the jev overrides that sit above a `[jev]` key (Phase 34).

- `GSD_PATH_JEV`: the session override of `[jev] enabled`: `1` turns jev on, any other non-empty
  value off, unset leaves the files' choice (`KNOB_ENV`, `jev_config.py:617`).
- `JEV_LAYA_URL`, then `AI_KIT_LAYA_URL`: the session override of `[jev] laya_url`, any address; a
  host off loopback needs consent (`URL_ENV`, `jev_config.py:616`). The default is
  `LAYA_DEFAULT_URL` (`jev_review.py:103`).
- `LAYA_API_KEY`: a credential read from the environment (`jev_review.py:767`).
- `JEV_LAYA_MODEL` (`jev_review.py:1063`), `JEV_TYPESAFE_URL` (`jev_review.py:957`),
  `JEV_TYPESAFE_MODEL` (`jev_review.py:1092`).
- `JEV_BACKEND` (`jev_review.py:1177`), `JEV_ALLOW_REMOTE` (`jev_review.py:1204`),
  `JEV_MIN_CONFIDENCE` (`jev_review.py:1399`).
- `GSD_PATH_JEV_TIMEOUT_SECONDS` (`jev_review.py:2040`).
- `GSD_PATH_JEV_DEADLINE_SECONDS` (`jev_review.py:2053`).
- The status-line override names: `CC_AI_KIT_CONFIG_FILE` and `AI_KIT_CURSOR_CONFIG_FILE` take the
  host's env prefix (`tools/common_config.py:281`).
- `AI_KIT_KEEP_MIGRATION_BACKUP`: `1` keeps an old `review-spec.toml` as `review-spec.toml.migrated`
  after its migration; unset or any other value deletes it once the migration's value check passes
  (by default; a file that changed during the run stays under its name, named in a warning, and a failed
  final migration removal leaves a `review-spec.toml.retiring` copy to remove by hand) (`keep_backup_from_env`, `config_migrate.py:61`). `render-toml --keep-backup` sets it
  for one write.

## Other tools' files

ai-kit writes another tool's config only through that tool's documented keys (D-17). The record lists
each write site; `tests/test_config_callers.py` (TestForeignKeys) scans the Python and the runner
template for writes to a GSD config and fails on any site it does not allow.

- GSD `.planning/config.json` (and `.planning/workstreams/<ws>/config.json`). The runner reads
  `workflow.cross_ai_timeout` from the scoped files (`scopedConfigPaths`, `cross-ai.mjs:3032-3041`).
  The runner's one-time migration removes the legacy `workflow.cross_ai_retry` block by temp file and rename: the
  span scanner `findJsonKeySpan` (`cross-ai.mjs:3668`) and `removeRetryBlock` (`cross-ai.mjs:3691`)
  find it, and `writeFileAtomic` (`cross-ai.mjs:3595`) publishes the file, so every other byte stays.
  The migration is `migrateRetrySources` (`cross-ai.mjs:3898`). A block added again later is ignored
  with a notice. GSD keys written by ai-kit go through `gsd-tools config-set`, which rejects keys
  outside gsd-core's list (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:263`), and curated-config
  writes its pairs through `_write_config_pairs` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:111`).
- GSD runner copy `.planning/scripts/cross-ai.mjs`: curated-config renders it from the shipped
  template with a baked `// <config>` block (`runner_config`, `cross_ai_script.py:93`; `render`,
  `cross_ai_script.py:141`) and publishes it with `cache_write_bytes` (`cross_ai_script.py:218`),
  through `ensure_runner` (`cross_ai_script.py:358`). ai-kit-spec-review rewrites the shipped
  template atomically (`skills/ai-kit-spec-review/ai_kit_spec/cross_ai_catalog.py:46`). The baked
  block is the runner's own `CONFIG`; it is not a setting ai-kit reads from `config.toml`.
- curated-config backups: `_atomic_copy` (`config_backup.py:49`) and `restore_backup`
  (`config_backup.py:148`). The restore receives the config path as a parameter and writes back GSD's
  own earlier bytes; the test scan does not see it, and this record lists it for that reason.
- Claude `settings.json` (statusLine, hooks): `wire_claude_rows` (`tools/setup.py:2212`) and
  `wire_statusline` (`tools/setup.py:2385`), published by `_atomic_write_json` (`tools/setup.py:2056`).
  Plain JSON, so comments do not apply.
- Cursor `cli-config.json` and `hooks.json`: `wire_hook_cursor` (`tools/setup.py:2261`) and
  `wire_statusline_cursor` (`tools/setup.py:2682`). A JSONC file with comments is refused, not rewritten.
- opencode config: `_apply_opencode_share_mode` (`tools/config_doctor_checks.py:270`) through
  `set_jsonc_value` (`tools/config_doctor_appliers.py:376`), published by `atomic_write_text`
  (`tools/config_doctor_appliers.py:114`). The splice keeps comments.
- Codex `config.toml`: `_apply_codex_history_persistence` (`tools/config_doctor_checks.py:362`) through
  `_upsert_toml_table_key` (`tools/config_doctor_checks.py:324`) and `write_toml_region_replace`
  (`tools/config_doctor_appliers.py:69`). The table-region splice keeps comments.
- Global rules files (`CLAUDE.md`, the Codex and opencode `AGENTS.md`, `GEMINI.md`):
  `_commit_global_rules` (`tools/setup.py:4141`).
- systemd user units for session wake: the atomic text writer `write_text_atomic`
  (`skills/ai-kit-session-wake/ai_kit_session_wake/state.py:99`) and the unit folder
  (`skills/ai-kit-session-wake/ai_kit_session_wake/units.py:41-44`).

The config doctor's host writes keep to each host's documented keys, and the record lists them here so
a reader can check that claim.

## State and caches

State is persistent and machine-written; a cache is rebuilt when it is lost.

- Unit stack record `<git common dir>/ai-kit-stack.json` (`RECORD_NAME`, `flow_record.py:24`), written
  by `write_record` (`flow_record.py:155`) atomically. Per repository, never committed.
- Restack state `<git common dir>/ai-kit-restack.json` (`RESTACK_NAME`, `flow_stack.py:38`), written
  atomically.
- Index refresh queue `<git common dir>/ai-kit-index-queue` and its lock (`QUEUE_NAME`,
  `flow_index.py:28`).
- Unit brief `.aikit/brief/SKILL.md` (`BRIEF_REL`, `flow_brief.py:21`), a generated artifact written
  atomically.
- Runner quota cycles `${XDG_STATE_HOME}/ai-kit/spec/cycles/...` written by `writeCycleState`
  (`cross-ai.mjs:4184`) through a temp file and rename.
- Session wake state `${XDG_STATE_HOME}/ai-kit/session-wake/...` written atomically by `_atomic_write`
  (`skills/ai-kit-session-wake/ai_kit_session_wake/state.py:75`) and `write_text_atomic`
  (`state.py:99`).
- jev answer log `${XDG_STATE_HOME:-~/.local/state}/ai-kit/jev-answers.jsonl`
  (`answer_log_path`, `jev_review.py:1937-1939`), one JSON line per item.
- jev learning records `${XDG_STATE_HOME:-~/.local/state}/ai-kit/jev/laya-capabilities.json` and
  `typesafe-models.json` (`records_path`, `jev_learn.py:65`), written atomically by
  `write_records` (`jev_learn.py:96`); per user, never committed. A key's record stays until the
  key changes, and `--check-updates` refreshes it.
- Usage-metrics store `${XDG_DATA_HOME:-~/.local/share}/ai-kit/usage-metrics`
  (`skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py:15`).
- Model catalog cache `${XDG_CACHE_HOME:-~/.cache}/ai-kit/spec/model-catalog.json` (`model_catalog.py:54-55`),
  with `_meta` reserved for cache metadata.
- Runtime snapshot and quota caches under `${XDG_CACHE_HOME:-~/.cache}/ai-kit/spec/` (`cache_base`,
  `cache.py:9-12`).
- Status-line provider and git caches under the cache folder (`cfg_cache_base`,
  `tools/common_config.py:503`).
