# ai-kit's config file

**Read this when** a question is about where the config wizard writes, the layers, another table in the file, the migration of an old roster, or trust; at SKILL.md Step 2.1 for "Layers", at Step 2.8 for "Roles", and at Step 3 for "Lane entry fields" and the example below it.

## Layers

ai-kit keeps its settings in `config.toml`, one file per layer:

- **Project:** `.aikit/config.toml` in the project root.
- **User:** `$XDG_CONFIG_HOME/ai-kit/config.toml` when `XDG_CONFIG_HOME` is an absolute path, else `~/.config/ai-kit/config.toml` (a relative or blank value counts as unset).

The reader merges the two per key. A key the project file sets wins; a key it does not set comes from the user file, and then from the built-in default. A lane list is merged per role. `strategy = "local-only"` in the project file keeps the user file out of the roster.

A missing file is the normal empty state: no roster, built-in defaults, and nothing is written until a command saves a value. A file that does not parse stops the CLIs with exit 2 and names the file.

**The wizard's write target (SKILL.md Step 2.1).** Its `<user config>` is the user file above (the same rule the config reader uses; a relative or blank `XDG_CONFIG_HOME` counts as unset), resolved once to an absolute path. A file holds a roster when it has a `[lanes]` table, or when an old `review-spec.toml` sits beside it (it migrates into that config.toml on the write); a config.toml with neither counts as no roster. What the replacement gate showed is the target's `[lanes]` table as Read, or the old file beside it.

## Tables

| Table | Meaning |
| --- | --- |
| `[lanes]` | The roster. `strategy` is `global-merge` (the default, so the key is omitted) or `local-only`. |
| `[lanes.policy]` | `mode` and `timeout_tiers` (seconds). A legacy flat `ladder` here loads as each role's order, filtered to that role's lanes, and the next write replaces it. |
| `[lanes.policy.review]` | `ladder`: the priority order of the review lanes (lane keys; the first available wins). |
| `[lanes.policy.execute]` | `ladder`: the priority order of the execute lanes. `session_fallback = true` (written only on the owner's yes): when no execute lane is available, the superpowers execute adapter runs the task on the session's own model. Removing it revokes the flag in the file written; the effective value follows the layer rules (a project `[lanes.policy.execute]` table replaces the user's). |
| `[[lanes.review]]` | One entry per review lane. |
| `[[lanes.execute]]` | One entry per execute lane. |
| `[runner]` and `[runner.retry]` | Retry tuning for the cross-AI runner. |
| `[runner.retry.scopes."<scope>"]` | Retry values for one named scope. |
| `[models]`, `[jev]`, `[hooks]` | Filled by other features. The wizard does not write them. |

A lane entry carries `key`, `runtime`, `model`, the knobs of its runtime (`effort`, `service_tier`, `cursor_mode`), `purpose`, `strength`, `is_router`, `fallback_quota` and `timeout_tiers`. A custom entry has a `command` in place of `runtime`.

The wizard writes only the `[lanes]` roster. It keeps every other table, every unknown key and every comment, except the comments of a lane entry or policy table the new roster drops: those go with it (copy the file first to keep them).

## Roles

The `purpose` of an entry decides its role:

- `review`, or no `purpose` at all, goes to `[[lanes.review]]`.
- `execute` goes to `[[lanes.execute]]`.
- `both` gives one entry in each role, with the same keys.

Every key is kept, `purpose` included. A lane is never shared across roles: a lane that serves both roles is two entries, and changing one never changes the other. Each role's priority order is the `ladder` of `[lanes.policy.review]` or `[lanes.policy.execute]`; a key in it that names no lane of that role is dropped with a warning, a role with no lane gets no order table, and the project layer's role table replaces the user's for that role. `render-toml` keeps a generated `#` comment with each order above its `[lanes.policy.review]` or `[lanes.policy.execute]` table, so it stays readable to anyone opening `config.toml` later.

`policy.mode` decides the review seats: `single` seats the first available lane of the review order whose vendor differs from the document author's, else the first available lane; `double` seats the first available lane and adds a secondary from another vendor only when one is available.

## Lane entry fields

**Read this at SKILL.md Step 3, before building `lanes`.** Each object in `lanes` carries:

- `key`; `runtime` and `model` (or neither, for the session default; `command` only on a custom entry for a CLI outside the runtime table).
- `vendor` from Step 2.3 on every entry with a `model`, the claude-host alias pair of Step 2.7 included: the `infer-vendor` value, or the owner's answer when it printed null; no `vendor` key when the owner chose to save the lane without one. The reviewer pick treats such a lane's vendor as unknown: the cross-vendor filter never skips it, so in `single` mode it can be seated as the different-vendor reviewer even when its real vendor is the document author's, and when it is the `double` primary the secondary only has to differ from the author's vendor. The session default (no `runtime`, `model = ""`) has none: its vendor is whatever the host runs, and the reviewer pick reads only the stored vendor for its cross-vendor filter.
- `purpose` (`review`, `execute` or `both`, from Step 2.2 or Step 2.7). Every newly registered entry gets an explicit `purpose`; an absent `purpose` is reserved for a pre-migration entry carried forward unchanged.
- Its knobs (`effort`, `service_tier`, `cursor_mode`) and `strength`; `effort_source` only after a test call accepted that effort.
- `is_router` or `fallback_quota` only when confirmed `true`; `escalate_runtime` or `escalate_model` only when `true`; `usage_limited` (and `usage_limit_note`) only on the owner's yes.
- `pool` on every zero-price lane, and the data-use keys on every zero-price lane the owner confirmed (`free-lanes.md`).
- A flat `timeout_tiers` list on a lane the owner gave its own tiers (SKILL.md Step 2.8); on a custom entry, the fields its `command` template names as placeholders (`references/runtime-ids.md`).

Never write a `false` flag.

**Check every entry's keys against this list before the write.** `render-toml` refuses some bad values and prints why, but it keeps an unknown key as written: a misspelled knob such as `servce_tier` is saved silently and still exits 0, so the runner never sees the tier the owner chose. Fix a key outside this list (or ask the owner about it) before calling `render-toml`.

## Example: the JSON the wizard passes to render-toml

An example only: the keys are the ones the wizard writes; the ids and values are placeholders, and YYYY-MM-DD stands for the date of the run. Each role has its own order under policy; a lane carries only the settings the owner chose, and a flag appears only when it is true.

```json
{
  "policy": {
    "mode": "single",
    "timeout_tiers": [
      600,
      1200,
      1800
    ],
    "review": {
      "ladder": [
        "review-main",
        "review-second",
        "review-third"
      ]
    },
    "execute": {
      "ladder": [
        "execute-free",
        "execute-main"
      ]
    }
  },
  "lanes": [
    {
      "key": "review-main",
      "runtime": "codex",
      "model": "placeholder-model-1",
      "vendor": "fake-vendor-a",
      "purpose": "review",
      "effort": "high",
      "escalate_runtime": true,
      "escalate_model": true
    },
    {
      "key": "review-second",
      "runtime": "pi",
      "model": "placeholder-model-2",
      "vendor": "fake-vendor-b",
      "purpose": "review"
    },
    {
      "key": "review-third",
      "runtime": "codex",
      "model": "placeholder-model-5",
      "vendor": "fake-vendor-a",
      "purpose": "review"
    },
    {
      "key": "execute-free",
      "runtime": "opencode",
      "model": "fake/placeholder-model-3",
      "vendor": "fake-vendor-c",
      "purpose": "execute",
      "effort": "high",
      "effort_source": "accepted by a call on YYYY-MM-DD",
      "usage_limited": true,
      "usage_limit_note": "about 100 requests a day",
      "pool": "fake:free",
      "data_use": "may_be_kept_or_trained",
      "data_use_line": "The provider's page says prompts may be kept and used for training.",
      "data_use_source": "https://example.com/data-use",
      "data_use_read": "YYYY-MM-DD",
      "data_use_label": "reported",
      "data_use_confirmed": true
    },
    {
      "key": "execute-main",
      "runtime": "codex",
      "model": "placeholder-model-4",
      "vendor": "fake-vendor-a",
      "purpose": "execute"
    }
  ]
}
```

- effort is the lane's effort level in the runtime's own form; effort_source is present only when the level was learned by an accepted test call.
- escalate_runtime and escalate_model are opt-in flags for fix rounds 4 and 5 of a stuck task: `escalate_runtime` allows a more capable lane ranked above it in the role's order with another runtime, `escalate_model` one with the same runtime and another model; the superpowers execute adapter reads them at fix rounds 4 and 5, and the runner reports them as ignored and never starts another lane from them.
- usage_limited is the owner's yes that the lane has a usage cap, with an optional one-line usage_limit_note; pool names the lane's free tier (<provider>:free) and is written on every zero-price lane. A flagged lane falls back to the first lane of its role, in the role's order, that is neither flagged nor in the same pool; the review run and the execute adapter read the flag after that lane's quota stop.
- The data-use record of a free lane has five required keys, data_use, data_use_line, data_use_source, data_use_read and data_use_confirmed (always true), plus data_use_label only when data_use is not unknown. render-toml writes a lane with a pool only together with that record; a lane the owner declined or skipped is not written.

## Lane settings

These keys sit flat on one lane entry. A project entry that changes a user lane's `runtime`, `command` or `model` drops every one of them that it does not restate.

- `effort`: the lane's effort level, on any runtime. The runner passes it in the runtime's own form where it has a path (codex as a flag; pi, cursor and opencode inside the model id); elsewhere every preview and dispatch prints `ignored: <reason>`. `effort_source` (`accepted by a call on <YYYY-MM-DD>`) is written only after a test call with that effort answered.
- `escalate_runtime`, `escalate_model`: booleans, written only when `true`; at fix rounds 4 and 5 of a stuck task the target is a more capable lane of the same role, ranked above it in that role's order, with another runtime or with the same runtime and another model. The superpowers execute adapter reads them at fix rounds 4 and 5; dispatch also passes them to the runner (`--escalate-runtime`, `--escalate-model`), which reports them as ignored (`recorded_only`) and never starts another lane from them.
- `usage_limited` (written only as `true`, on the owner's yes) and `usage_limit_note` (display text, never parsed). The review run and the execute adapter read `usage_limited` after that lane's quota stop; `usage_limit_note` stays display text.
- `pool`: `<provider>:free`, written on every zero-price lane. A usage-limited lane's fallback is the first lane of the same role, in that role's order, that is neither usage-limited nor in the same pool.
- The data-use record of a zero-price lane, written only on the owner's yes: `data_use` (`zero_retention`, `may_be_kept_or_trained` or `unknown`), `data_use_line`, `data_use_source`, `data_use_read`, `data_use_label` (`verified` or `reported`, absent for `unknown`) and `data_use_confirmed` (`true`). A declined or skipped confirmation writes no lane.

## Trust

Trust covers the project file's command-bearing lane entries. **Command-bearing** (the one definition, which the skill's Step 4 uses; the same as `trust.command_lanes_bytes`): an entry with a `command`, or an entry whose `key` equals the `key` of a `command` entry in this file or in the user layer (only without `strategy = "local-only"`): the user `config.toml`'s `[lanes]`, or, when it has none, an old `review-spec.toml` beside it pending migration, read in memory (`config_io.cfg_project_trust_bytes`), in any role. Such an entry's fields fill the command's placeholders, so a `runtime` entry that overrides a user command entry counts. A plain (runtime, model) pair with its own key is not command-bearing.

- Editing another table, a comment or the spacing keeps trust.
- Changing a command-bearing entry, or adding one, needs a new trust.
- A project file with no command-bearing entry needs no trust.

A trust record lives under `config-trust/` in the user config folder. It is tied to the file's real path and to a digest of its command-bearing entries. While a project file that needs trust is untrusted, its whole `[lanes]` table is ignored (not only the command-bearing entries), and the CLIs print `ignoring untrusted project-local config`.

`trust-local --show` records no new trust, but it is not a pure read: like every `trust-local` call it first migrates a pending old `review-spec.toml` (`trust-flow.md` step 1). It prints one line per project entry that runs as a subprocess (a `runtime` or a `command`, so more entries than the command-bearing ones), each with its argv and whether the file is trusted. `trust-local` records trust after an explicit yes, and `trust-local --revoke` withdraws it.

## Migration from review-spec.toml

- The first command that reads the roster migrates an old `review-spec.toml` in the same folder into the `[lanes]` table of that layer's `config.toml`.
- By default the old file is deleted once the migration's value check passes. With `AI_KIT_KEEP_MIGRATION_BACKUP=1` in the environment, or `render-toml --keep-backup`, it is renamed to `review-spec.toml.migrated` instead. A failed check deletes and renames nothing. An old file that changed during the run is kept (under its own name, or as `review-spec.toml.migrated` when that name is taken) and named in a warning; one that cannot be moved aside stays and the next read finishes the job; when the final removal fails, a `review-spec.toml.retiring` copy is left, named in a warning, to remove by hand.
- A trust that the old file held carries over to the new file. An untrusted roster stays untrusted.
- The migration prints one line that names both files and no values.
- An existing `[lanes]` table in `config.toml` wins. The old file is reported and never merged in.
- The read-only checks (`--check-only`, `check-providers` and `probe-quota --no-migrate`) report `migration pending` (`migration held` for an old roster that names a removed runtime) and write nothing.
- An old roster with a lane that names a removed runtime is never migrated by a read: each read uses it in memory without that lane and prints one `migration held` line that names the file and the re-save command (the ai-kit-spec-config wizard, or `render-toml --out <config.toml> --replace`). `config-status` reports that file as `migration-held`, and its first line counts the remaining lanes (`active`, or `none` when no lane is left). A held project roster whose remaining lanes need trust that the old file does not have is ignored by every read, like an untrusted project `config.toml`: `config-status` reports it as `migration-held-untrusted` with the first line `pending`, and `trust-local` migrates it and records the trust.
- `render-toml` treats an old roster beside its target as an existing roster. Without `--replace` it refuses and migrates nothing. With `--replace` it migrates the old file first and then writes.

## Read-only commands

- `config-status --cwd <project root>` prints `active`, `pending` or `none` on its first line, then one `checked` line per file it read, project first, then one removal line per lane that names a removed runtime (the `ai-kit-spec: <file> [<role> <key>]: runtime ... was removed from ai-kit ...` note a load prints on stderr), then, when the state is `active`, one `capability` line per effective lane. It writes and migrates nothing; the review skill and the execute adapter run it before they read lanes.
- `propose-lanes --purpose review` (or `execute`) prints the ranked shortlist of one purpose from the model catalog as JSON and writes nothing.

## Files kept apart

Trust records, consent, secrets, the model catalog cache, the unit flow's `.aikit/flow.json` and the status-line files stay in their own files; the design record in the ai-kit repository (`docs/config/design.md`) lists each one with its reason.
