# Phase 33: One config design - Context

**Gathered:** 2026-11-13 (auto draft) · **Rewritten:** 2026-11-14 (owner decisions, after the rewritten 33-SPEC.md)
**Status:** Ready for planning (the draft plans 33-01..33-11, RESEARCH, PATTERNS and VALIDATION are superseded, D-23)

<domain>
## Phase Boundary

ai-kit keeps its settings in one neutral `config.toml` per layer: project `.aikit/config.toml` over user
`${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`, per key, with one table per concern and role-keyed lane entries.
The reviewer roster leaves `review-spec.toml`, the runner's retry tuning leaves GSD's `config.json` and the user
`cross-ai.json`, each migrating once with nothing lost. ai-kit writes no key into another tool's schema and runs in a
repository without `.planning/`. Machine-written state (trust records, consent, secrets, the catalog cache, the unit
flow's `flow.json`, the status-line host files) stays in its own files with a recorded reason.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** See `33-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `33-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** the inventory and decision record with its test (R1, R2); `config.toml`, its tables,
reader and comment-keeping atomic writer, the roster migration with trust re-keyed, every caller and doc moved
(R3-R6); the runner's TOML-subset reader, retry sources and both retry migrations (R7); the no-foreign-key rule and
the no-GSD run (R8); atomic lossless writes (R9); one resolver rule (R10); docs and loop `33` (R11).

**Out of scope (from SPEC.md):** moving the state files into `config.toml`; the later phases' keys and flows (34, 35,
36, 38.1, 49); real GSD keys; bringing spec-review or cross-ai to the bar; the draft's plans.
</spec_lock>

<decisions>
## Implementation Decisions

### Owner decisions (2026-11-14, locked; they replace the 2026-11-13 draft's D-01, D-02, D-03, D-06, D-12-D-15)

- **D-01: One neutral `config.toml` per layer, one table per concern; no file named after a skill or a host.** The
  owner rejected `review-spec.toml` holding other commands' settings and asked for either one neutral, well
  structured file or one file per skill. One file wins because the lanes, the runner retry and the jev settings are
  shared by several skills (spec-review, spec-execute, the superpowers adapter, curated-config, the runner), so a
  per-skill split would duplicate or cross-reference them. jev: choice 0.91 (typesafe: one config.toml per layer,
  table per concern, state files apart); laya low 0.39, same choice. The draft's objection (a shared file breaks the
  byte-pinned trust) is answered by D-11.
- **D-02: The user layer stays in `${XDG_CONFIG_HOME:-~/.config}/ai-kit/`; the project layer is `.aikit/`.** The
  owner asked about `~/.aikit`; the existing XDG directory already holds the status line, consent and trust files and
  honours `XDG_CONFIG_HOME`. jev: choice 0.82 (typesafe: keep XDG); laya low 0.46 (none of these).
- **D-03: Tables of `config.toml`** (documented in the record with keys and the phase that fills each):
  - `[models]` — catalog sources (models.dev, Artificial Analysis, LM Arena), cache age and classification settings;
    Phase 35 fills it. Not read in this phase.
  - `[lanes]` — `strategy` and the `[lanes.policy]` keys moved from the roster's top level and `[policy]`;
    `[[lanes.review]]` — one entry per review lane (the old `[[reviewers]]` keys, unchanged);
    `[[lanes.execute]]` — one entry per execute (coding) lane, same entry keys; Phase 36 adds selection, ranking and
    escalation flags. A lane is never reused across roles.
  - `[runner]` — `migrated_from` marker (D-14); `[runner.retry]` — the five `cross_ai_retry` keys;
    `[runner.retry.scopes.<scope>]` — per-GSD-scope values (D-15).
  - `[jev]` — Phase 34's Laya URL, the on/off knob and the Laya capability cache settings. Not read in this phase.
  - `[hooks]` — Phase 49's switches. Not read in this phase.
- **D-04: Assignments of every inventory row** (the R2 table): moves now — the roster (both layers) into `[lanes]`,
  the project GSD retry block and the user `cross-ai.json` into `[runner.retry]`; stays separate with a reason — the
  trust records (consent records, renamed store `config-trust/`), `jev-consent.json` (consent), `secrets.env`
  (credential, never merged), the model catalog cache (machine-written data, `_meta` reserved), `cross-ai-errors.json`
  (a user data overlay the runner loads as a JSON array, not a setting), `.aikit/flow.json` (the unit flow's own,
  absorbed with commit-fold in Phases 45-47), and the status-line `claude-statusline.toml`, `cursor-statusline.toml`
  and `segments*/` (the status-line tool's own files, written and patched by its wizard and doctor; not a skill
  setting); named now, filled later — `[models]`, `[lanes.execute]` selection, `[jev]`, `[hooks]`.

### Record and test (SPEC R1, R2)

- **D-05: The record is `docs/config/design.md`** (inventory, decision, tables, assignments, the trust rule, the
  resolver rule), built from `tmp/auto/33-inventory.md` with its `file:line` cites refreshed at execution. Tests may
  read `docs/`, never `.planning/`. (kept from the draft's D-04)
- **D-06: The fitness test `tests/test_config_design_record.py`** collects the file names from the path functions
  (`cfg_local_path`, `cfg_global_path` and their new equivalents, the trust store, `consent_path`,
  `secrets_env_path`, `cfg_config_path`, the flow settings path, the runner's files), asserts each appears in the
  record with exactly one assignment, and fails when a new path or table carries a skill or host name.

### Format, reader and writers (SPEC R3, R7, R9)

- **D-07: TOML everywhere ai-kit keeps settings; the runner gets a TOML-subset reader.** Python reads with `tomllib`.
  The runner (node built-ins only) gains `readTomlSubset`: tables and dotted table headers, `key = value` with basic
  strings, integers, floats, booleans and arrays of numbers or strings, comments; anything else (inline tables,
  multi-line strings, dates, arrays of tables outside `[lanes]`) makes it skip that file with one notice and fall to
  the next source. It reads only `[runner]` and `[runner.retry*]`; `[[lanes.*]]` blocks are skipped as opaque.
- **D-08: The writer is a region splicer in `ai_kit_spec` (`toml_splice.py`), modelled on the tools/ helpers, not
  imported.** It understands tables and arrays of tables: an unchanged table keeps its text byte for byte; a changed
  key is rewritten on its own line; an added entry goes after the last entry of its array or at the end of its
  table; a removed entry's lines go; unknown tables and comments outside the changed lines are kept. It re-parses the
  result with `tomllib` and refuses to publish unless it equals the intended document. It replaces
  `cfg_render_toml`'s full rewrite (`render-toml` keeps its CLI and `--replace` guard). (draft D-07, generalised)
- **D-09: Publishing is atomic everywhere.** Python: `cache_write_bytes` gains an fsync of the file and its folder;
  new files get `0600`. The runner: temp file in the target folder, fsync, `renameSync`. The status-line recovery
  keeps its `.bak` copy, then publishes through a temp file and `os.replace`. (draft D-08)

### Roster migration and trust (SPEC R4-R6)

- **D-10: One migration module (`ai_kit_spec/config_migrate.py`) is the only Python code that names
  `review-spec.toml` or `review-spec-trust`.** It runs once before the read from `cfg_resolve`, `trust-local` and
  `render-toml`; `check-providers` and spec-config's `--check-only` read a legacy file read-only and report
  "migration pending". (draft D-09)
- **D-11: Trust pins the project file's realpath plus a canonical digest of its command-bearing lane entries.** The
  digest is sha256 over the canonical JSON (sorted keys, no spaces) of the ordered list of `(role, entry)` for every
  lane entry that has a `command` key. Editing another table, comments or spacing keeps trust; any change to a
  command-bearing entry (or adding one) needs a new trust; a file with no command-bearing entry needs none. Migration:
  if the old file is trusted under the old raw-byte rule, a record for the new realpath and digest is written in
  `config-trust/` before the old file is retired; an untrusted file gets none. This narrows what the HARD-03/05 gate
  hashes, so `/gsd-secure-phase` reviews it explicitly (threat: an attacker who can edit `.aikit/config.toml` but not
  a command entry gains nothing; one who edits a command entry loses trust, as today).
- **D-12: Migration steps, per layer.** (1) parse the old file (malformed or non-UTF-8 → `ConfigError`, exit 2,
  nothing migrated); (2) build the `[lanes]` table: `strategy` and `[policy]` keys under `[lanes]`/`[lanes.policy]`,
  each `[[reviewers]]` entry as `[[lanes.review]]` with its keys and the comment lines directly above it; file-level
  comments go above `[lanes]`; legacy fields are kept as written; (3) splice it into the layer's `config.toml`
  (creating it if absent; an existing `[lanes]` there means the new roster wins: report the old file, never merge);
  (4) re-read and compare parsed values; (5) carry trust (D-11); (6) rename the old file to
  `review-spec.toml.migrated`; (7) print one notice naming both paths. (draft D-10, adapted to a shared file)

### Runner retry (SPEC R7)

- **D-13: Sources and the migrations live in the runner.** `resolveRetry` reads `[runner.retry]` (and the active
  scope's table) from the project `config.toml`, then the user one, then `CONFIG.retry`, then `RETRY_DEFAULTS`, per key
  with today's validation. GSD calls the runner directly, so the runner itself migrates: the GSD block is removed by a
  JS span scanner (ported from `find_object_span`/`_find_top_level_key_span`), writing beside the realpath so a
  symlinked `config.json` stays a link; the user `cross-ai.json` is renamed `cross-ai.json.migrated` after its values
  land in the user `config.toml`. Values are written with a line splicer that appends the `[runner.retry]` table when
  absent or inserts missing keys under it, then re-reads with `readTomlSubset` before publishing. The "Nothing here
  writes a config file" comment (`cross-ai.mjs:3206`) is rewritten. (draft D-13, retargeted)
- **D-14: Write order and the marker.** (1) merge values into the target `config.toml` (its own keys win; a
  conflicting source value is named in the notice); (2) remove the GSD block or rename the user JSON; (3) record the
  source files in `[runner] migrated_from`. A block later found in a recorded file is ignored with a one-line notice.
  A run cut off after (1) re-merges identical values and finishes. (draft D-14)
- **D-15: Per-scope values are kept.** A workstream's or GSD project's own block lands under
  `[runner.retry.scopes."<scope>"]` keyed by the scope the runner resolves today, read before the top level for the
  active scope. The notice says the project file is per checkout and may be git-ignored. (draft D-15)
- **D-16: Only the template `skills/ai-kit-spec-review/references/cross-ai.mjs` is edited;** the dogfood copy is
  re-rendered and `make check-dogfood` proves it pristine; new self-test cases follow SPEC R7 plus the subset reader's
  refusals, each with its kind, and the shard timings are refreshed. (draft D-16)

### Foreign schemas and GSD independence (SPEC R8, owner 2026-11-14)

- **D-17: ai-kit writes another tool's config only through that tool's documented keys.** GSD keys go through
  `gsd-tools config-set` (which rejects unknown keys); the runner's only direct GSD write is removing the legacy
  block. A test scans ai-kit's Python and the runner template for writes to `.planning/**/config.json` and fails on
  any path other than `gsd-tools config-set` and the block removal; another asserts no ai-kit writer emits
  `cross_ai_retry` into a GSD config. The config doctor's host writes (Claude, opencode, Codex) already keep to each
  host's documented keys and are listed in the record.
- **D-18: No `.planning/` needed.** The runner looks up `.planning/` only to migrate the legacy block and to read
  `workflow.cross_ai_timeout`; with no `.planning/` it reads ai-kit's files only and prints nothing about GSD. A
  scratch-repo test without `.planning/` runs `resolve-reviewers`, the runner's retry resolution (self-test case) and
  spec-config `--check-only`, and asserts no `.planning/` is created.

### Resolver, docs and judging (SPEC R10, R11)

- **D-19: One resolver rule, implemented once per code boundary, with a parity test** (`config_io`,
  `local_secrets`, a copy in `jev_review`, one function in `tools/common_config.py`, a JS copy in the runner);
  `tests/test_config_dir_parity.py` runs every copy on absolute, relative, empty and whitespace `XDG_CONFIG_HOME` and
  no home. (draft D-17)
- **D-20: Docs.** `ai-kit-spec-config` SKILL.md and references describe `config.toml`, its tables, the layers, the
  migration and the record; the README gains an "ai-kit configuration" section; curated-config's retry guidance moves
  to `[runner.retry]`; the cross-ai, spec-review, checklist and superpowers references get the new names. (draft
  D-18, renamed)
- **D-21: Loop `33` judges `ai-kit-spec-config` and `ai-kit-gsd-curated-config` only;** fact-only name and path
  updates elsewhere are not material and are listed as stale-digest notes. Judges referee-one and referee-two;
  referee-three replaces one that fails; one usable referee is accepted with the reason recorded; never native opus.
  (draft D-19)

### Later phases and the draft

- **D-22: 33 ships the layered reader and splicing writer as reusable code and creates `config.toml` with `[lanes]`
  and `[runner]` only.** `[models]`, `[jev]` and `[hooks]` are documented, not created or read; Phases 34, 35 and 49
  read them through this reader (jev-fast-decision copies it with a parity test).
- **D-23: The 2026-11-13 agent draft's plans 33-01..33-11, RESEARCH, PATTERNS and VALIDATION are superseded.** They
  were written before the owner reviewed the design. They were moved to `.planning/research/2026-11-13-phase-33-agent-draft/` (tag
  `archive/phase-33-agent-draft` marks the draft tip) so no GSD scan sees them as this phase's plans; the phase is
  replanned from this CONTEXT.

### Claude's Discretion

- Module and function names inside `ai_kit_spec` beyond those named above; the exact notice wording (one line, both
  paths, no values); test module split within the runner's group rules.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/33-one-config-design/33-SPEC.md` — locked requirements, edge coverage, prohibitions.
- `tmp/auto/33-inventory.md` — the settings inventory with `file:line` cites (source for the D-05 record).
- `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`, `trust.py`, `cli.py`, `provider_check.py`,
  `local_secrets.py`, `cache.py`, `quota.py`.
- `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` (`assemble_candidates`).
- `skills/ai-kit-spec-review/references/cross-ai.mjs` (`aiKitConfigDir`, `readJsonObject`, `workflowValue`,
  `scopedConfigPaths`, `resolveRetry`, `writeCycleState`, self-test harness).
- `tools/setup.py` (`write_toml_preserving`, `create_if_absent`, `_recover_incompatible_config`,
  `_read_json_checked`, `_atomic_write_json`); `tools/config_doctor_appliers.py` (`find_object_span`,
  `_find_top_level_key_span`, `write_toml_region_replace`); `tools/common_config.py` (`cfg_config_path`).
- `skills/jev-fast-decision/scripts/jev_review.py` (`_config_dir`, `consent_path`).
- `skills/ai-kit-spec-config/SKILL.md` and `references/`; `README.md`.
- `.planning/ROADMAP.md` Phases 34, 35, 36, 38.1, 49 (the tables D-03 places; amended 2026-11-14).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ai_kit_spec.cache.cache_write_bytes`; `trust.record_trust`/`is_trusted`; `create_if_absent`'s publish-if-absent;
  `_KEY_RE` line patching; `find_object_span`/`_find_top_level_key_span`; `writeCycleState`; `jsonc_read.py`.

### Established Patterns
- Skills stay self-contained; `tools/` imports no skill (`tests/test_arch.py`); shared logic is copied with a parity
  test. A broken config stops the CLIs with `ConfigError` (exit 2). The runner falls through sources per key.

### Integration Points
- GSD calls the runner directly (`cross_ai_command`); spec-config writes through `render-toml`; the superpowers
  executor reads lanes through `cfg_resolve`.
</code_context>

<specifics>
## Specific Ideas

- The migration notice is one line naming the old and new path and never a value.
- The record's trust rule: "trust covers the project file's command-bearing lane entries; every other table is
  ordinary settings".
</specifics>

<deferred>
## Deferred Ideas

- Resolving the project layer from the main worktree so worktrees share it (not chosen: the roster is per checkout
  today).
- Moving the status-line host files into `config.toml` (D-04 keeps them with the status-line tool; revisit if the
  status line becomes a skill).

### Reviewed Todos (not folded)
- `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md` — its addendum (jev knob in
  the TOML config) is the D-03 `[jev]` place; the lane split, effort and escalation stay with Phase 36.
- Hooks todos (`2026-10-18-visible-tool-advisory-hooks-pre-and-post-tool-use.md`,
  `2026-10-24-make-the-ai-kit-session-hooks-dynamic-worktree-indexing-advi.md`) — Phases 48-49, `[hooks]` place.
</deferred>
