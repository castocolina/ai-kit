# ai-kit's config file

**Read this when** a question is about where the config wizard writes, the layers, another table in the file, the migration of an old roster, or trust.

## Layers

ai-kit keeps its settings in `config.toml`, one file per layer:

- **Project:** `.aikit/config.toml` in the project root.
- **User:** `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`.

The reader merges the two per key. A key the project file sets wins; a key it does not set comes from the user file, and then from the built-in default. A lane list is merged per role. `strategy = "local-only"` in the project file keeps the user file out of the roster.

A missing file is the normal empty state: no roster, built-in defaults, and nothing is written until a command saves a value. A file that does not parse stops the CLIs with exit 2 and names the file.

## Tables

| Table | Meaning |
| --- | --- |
| `[lanes]` | The roster. `strategy` is `global-merge` (the default, so the key is omitted) or `local-only`. |
| `[lanes.policy]` | `mode`, `ladder` (the priority order) and `timeout_tiers` (seconds). |
| `[[lanes.review]]` | One entry per review lane. |
| `[[lanes.execute]]` | One entry per execute lane. |
| `[runner]` and `[runner.retry]` | Retry tuning for the cross-AI runner. |
| `[runner.retry.scopes."<scope>"]` | Retry values for one named scope. |
| `[models]`, `[jev]`, `[hooks]` | Filled by other features. The wizard does not write them. |

A lane entry carries `key`, `runtime`, `model`, the knobs of its runtime (`effort`, `service_tier`, `cursor_mode`), `purpose`, `strength`, `is_router`, `fallback_quota` and `timeout_tiers`. A custom entry has a `command` in place of `runtime`.

The wizard writes only the `[lanes]` roster. It keeps every other table, every unknown key and every comment in the file.

## Roles

The `purpose` of an entry decides its role:

- `review`, or no `purpose` at all, goes to `[[lanes.review]]`.
- `execute` goes to `[[lanes.execute]]`.
- `both` gives one entry in each role, with the same keys.

Every key is kept, `purpose` included. A lane is never shared across roles: a lane that serves both roles is two entries, and changing one never changes the other. The order of entries inside a role is their priority order, and a write keeps that order.

## Trust

Trust covers the project file's command-bearing lane entries. **Command-bearing** (the same definition as the skill's Step 4 and `trust.command_lanes_bytes`): an entry with a `command`, or an entry whose `key` equals the `key` of a `command` entry in this file or in the user config (the user config only without `strategy = "local-only"`), in any role. Such an entry's fields fill the command's placeholders, so a `runtime` entry that overrides a user command entry counts. A plain (runtime, model) pair with its own key is not command-bearing.

- Editing another table, a comment or the spacing keeps trust.
- Changing a command-bearing entry, or adding one, needs a new trust.
- A project file with no command-bearing entry needs no trust.

A trust record lives under `config-trust/` in the user config folder. It is tied to the file's real path and to a digest of its command-bearing entries. While a project file that needs trust is untrusted, its whole `[lanes]` table is ignored (not only the command-bearing entries), and the CLIs print `ignoring untrusted project-local config`.

`trust-local --show` writes no trust record. It prints one line per project entry that runs as a subprocess (a `runtime` or a `command`, so more entries than the command-bearing ones), each with its argv and whether the file is trusted. `trust-local` records trust after an explicit yes, and `trust-local --revoke` withdraws it.

## Migration from review-spec.toml

- The first command that reads the roster migrates an old `review-spec.toml` in the same folder into the `[lanes]` table of that layer's `config.toml`.
- The old file is renamed to `review-spec.toml.migrated`, so its full text stays recoverable after the migration.
- A trust that the old file held carries over to the new file. An untrusted roster stays untrusted.
- The migration prints one line that names both files and no values.
- An existing `[lanes]` table in `config.toml` wins. The old file is reported and never merged in.
- The read-only checks (`--check-only`, `check-providers` and `probe-quota --no-migrate`) report `migration pending` and write nothing.
- `render-toml` treats an old roster beside its target as an existing roster. Without `--replace` it refuses and migrates nothing. With `--replace` it migrates the old file first and then writes.

## Files kept apart

Trust records, consent, secrets, the model catalog cache, the unit flow's `.aikit/flow.json` and the status-line files stay in their own files; the design record in the ai-kit repository (`docs/config/design.md`) lists each one with its reason.
