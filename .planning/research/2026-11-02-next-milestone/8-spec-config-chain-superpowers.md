# spec-config as the hub, the superpowers adapter, router-env models, shared code

Research date 2026-11-02. Read-only. Builds on `6-opencode-v2-and-lane-toml.md` (TOML schema,
`purpose` field, effort per runtime); that ground is not repeated. Scripts beside this file:
`8-list-models.sh` (opencode and `pi --list-models`, router-env rows only) and `8-pi-models.py`
(pi listing through ai-kit's own `detection.detect_pi_models`). No key was printed.

## 1. What each caller does today when no TOML exists

Short answer: nobody chains into spec-config. Review falls back to the session default and
mostly says nothing; superpowers execute stops with an empty "quota exhausted" result that names
no fix; the router does not look at config at all.

### ai-kit-spec-review

- When `ai-kit-spec.py` is missing it falls back to the session default with no error, on purpose:
  `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:52-54` ("treat this exactly like
  `--no-cross-ai` ... never block the review over it"). The same at `SKILL.md:151`.
- When the TOML is missing, `resolve-reviewers` returns `NO_CONFIG_FALLBACK`, the session default:
  `ai_kit_spec/quota.py:24-25`, `:167-191` (an empty ladder ends in `[NO_CONFIG_FALLBACK]`).
  `cfg_resolve` (`ai_kit_spec/config_io.py:389-415`) reads local, then global, and returns `{}` when
  neither file exists.
- The only hint is one line, `cross-ai-dispatch.md:139-145` ("No cross-AI config saved yet - run
  `ai-kit-spec-config` ..."). It prints only when the runtimes cache file did not exist yet, so
  only on the first run per machine. That cache lives about 30 days, so later runs without a TOML
  say nothing. The Step 5 line "every configured reviewer unavailable; reviewed with the session
  default" (`SKILL.md:161-163`) is about quota, not about a missing config.
- Python prints no warning of its own when no config exists (grep of `ai_kit_spec/*.py` finds none).

### ai-kit-spec-execute (router)

- It only detects the framework (`skills/ai-kit-spec-execute/SKILL.md:47-56`,
  `detect_framework.py`) and hands off to `-gsd` or `-superpowers`. It does not read
  `review-spec.toml` and has no config step. A missing `detect_framework.py` is a hard stop
  (`SKILL.md:20-25`). A missing adapter skill is not checked.

### ai-kit-spec-execute-superpowers

- Step 0 stops clearly when its own shim or the sibling `ai-kit-spec-review` directory is missing
  (`SKILL.md:56-72`). That is the one place today that "fails clearly" over missing scripts.
- When the TOML is missing, `assemble_candidates` (`ai_kit_spec_superpowers/dispatch_injection.py:165-189`)
  returns no candidates. `_cmd_resolve_injection` (`ai_kit_spec_superpowers/cli.py:265-271`) then
  emits `mode: "quota_exhausted"` with `tried: []` and `reasons: {}` (`cli.py:130-149`), exit 0.
  `references/resolution-stops.md:29-40` treats that as `any_quota_recoverable == False`: stop and
  "tell the user which key needs what fix". There is no key, so the user gets an empty stop that
  names neither spec-config nor a missing config.
- It never falls back to the session default for execution. The GSD adapter is clearer: it has a
  dedicated `no_configured_candidate` notice (`ai_kit_spec_gsd/adapter.py:272-278`).

### How spec-config is run and what it writes

- It is a skill with no scripts of its own: `skills/ai-kit-spec-config/` has only `SKILL.md` and
  `references/cli-model-selection.md`. Every action goes through ai-kit-spec-review's
  `ai-kit-spec.py`, found from the sibling directory first (`SKILL.md:23-57`). If that file is
  missing it stops with "ai-kit-spec-review's own `ai-kit-spec.py` module is missing".
- Flags (`SKILL.md:3`, `:66`, `:97-134`, `:169-181`):
  - `--check-only`: detects CLIs and reports quota without writing (it uses a throwaway path),
    and never runs `trust-local`.
  - `--local`: writes `./.aikit/review-spec.toml` without asking.
  - `--global`: writes `~/.config/ai-kit/review-spec.toml` without asking.
  - With neither flag the default target is local; it checks whether a global file exists and
    asks before replacing an existing file. `render-toml --out` refuses to overwrite unless the
    user agreed and `--replace` is passed.
- It writes one TOML through `render-toml` (`SKILL.md:393-436`, writer in `config_io.py:453-580`;
  see file 6 for the schema). Step 2.2 asks for each installed CLI whether it should be a reviewer
  (`SKILL.md:185-215`). The whole flow is worded as reviewer setup. `purpose` comes from Step 2.2
  and is optional (`SKILL.md:302`), and there is no separate "execute mode" pass. So spec-config
  cannot yet be asked "pick executors for me".

## 2. The superpowers adapter: pick, dispatch, effort, purpose

- **Roster**: the same shared roster as the GSD adapter, `[[reviewers]]` plus `policy.ladder`, read
  through `cfg_resolve` (`dispatch_injection.py:165-189`; duplicated on purpose so the two adapters
  stay independent).
- **Per-task pick** (`resolve-injection`, `cli.py:211-272`):
  1. `classify_task` and `estimate_required_context` on the task brief (`task_classification.py`).
  2. `resolve_execute_candidates` (`ai_kit_spec/execute_selection.py:115-151`):
     - screens entries that say `purpose = "execute"` on a CLI with no execute builder, or are
       custom commands (`:78-112`);
     - keeps purpose execute, both or unset, and falls back to everyone if none is left (`:29-35`);
     - filters by `task_affinity`, then `context_limit` (an unknown limit passes but ranks lower);
     - sorts by context known, then ladder position, then the affinity tie-break.
  3. Routing per candidate (native, subprocess, or a skip route such as `bad_model`,
     `review_only` or `not_installed`), computed once per call (`cli.py:203-208`, `_route_of` at
     `dispatch_injection.py:235-246`).
  4. Quota is refreshed only for subprocess candidates (`cli.py:172-185`). Then
     `resolve_ladder_pick` walks the ranked list (`dispatch_injection.py:323-346`) and returns the
     first candidate with quota.
  5. If no candidate survives the narrowing, the result is `no_candidate`. If every one fails quota
     or is skipped, it is `quota_exhausted` with typed reasons.
- **Escalation**: fix rounds 4-5 require a more capable model. The only capability signal is ladder
  order. `strength` is free text that no code reads (`references/escalation.md:23-28`). So the bump
  goes to a candidate ranked strictly above the stuck key. Nothing switches runtime on failure
  (NEVER list, `SKILL.md:31-33`).
- **Dispatch**:
  - native: the host's own subagent (on Claude Code, `Agent` with `model`).
  - external_cli: `dispatch-task` calls `dispatch_superpowers_task` (`dispatch_injection.py:364-394`),
    then `ai_kit_spec.execute_dispatch.dispatch_execute`, then `runner_dispatch.run_runner`
    (`runner_dispatch.py:586-619`). That runs `node <ai-kit-spec-review>/references/cross-ai.mjs`
    with the template path from `tooling_guidance.resolve_cross_ai_template_path`
    (`tooling_guidance.py:23-27`), in `--mode exec`.
  - It does not use the project's `.planning/scripts/cross-ai.mjs` (that is the GSD path) and has
    no runner of its own.
- **Effort**: `effort` and `service_tier` from the entry ride along in the injection
  (`_injection_for`, `dispatch_injection.py:303-307`). Only codex turns them into flags
  (`runner_flags`, `runner_dispatch.py:203-218`). For opencode, pi and cursor the effort is used
  only when the user baked it into the model id (`#high`, `:high`, `[effort=high]`); otherwise it
  is dropped without a message.
- **Purpose**: used only as the narrowing filter above (execute, both or unset), plus the hard
  error for `purpose = "execute"` on a review-only CLI. Superpowers execute and spec-review read
  one shared ladder, so the order cannot differ by role.

## 3. Live router-env models (2026-11-02)

`opencode models` (opencode 2.0.31), router-env rows:

    router-env/llama-cpp/ornith-15-9b
    router-env/my-coding
    router-env/my-coding-lite
    router-env/my-referee-one
    router-env/my-referee-three
    router-env/my-referee-two

pi lists the same six under provider `router-env`:
- `pi --list-models` prints a table (provider, model, context, max-out, thinking, images). Context
  sizes: referee-one 872K, referee-two 500K, referee-three 1M, my-coding 262K, my-coding-lite 262K.
- ai-kit's own path (`detect_pi_models`, which is pi RPC `get_available_models`,
  `detection.py:35-38`, `:576`) returns 190 models in total, including these six.
- pi reports `thinking: no` and empty `reasoning_modes` for all six. File 6 found that opencode's
  model API lists low/medium/high variants for router-env. So pi gives no way to check an effort
  for router-env models, and an effort check built on pi data alone would drop effort for them.

Confirmed: `my-referee-one`, `my-referee-two`, `my-referee-three`, `my-coding` and `my-coding-lite`
all exist today in both runtimes.
- Mismatch: both real TOMLs (`./.aikit/review-spec.toml:15`, `~/.config/ai-kit/review-spec.toml:34`)
  still name `router-env/my-plan-review`, which no longer exists, and contain no referee or
  my-coding entry.
- Only `.planning/config.json:55-63` (GSD review lanes) uses the referees.

## 4. `skills/_shared/`

- It holds one package, `ai_kit_rules_common` (classification, command_text, criticality,
  gsd_identity, makefile_parse, precommit_parse, remediation, stack_cache, stack_detect,
  tool_catalog, tool_presence, yaml_text). Only the `ai-kit-project-rules-*` family and the
  goal-prompt tests use it.
- How skills import it: the package `__init__` resolves its own real path (following symlinks),
  goes up to `skills/`, puts `skills/_shared` on `sys.path`, and raises an `ImportError` with an
  explanation when it is missing (`ai_kit_project_rules_agents/__init__.py:6-20`, the same in the
  makefile package). `pyproject.toml:55` puts `skills/ai-kit-spec-review` and `skills/_shared` on
  pylint's path.
- How it ships: `tools/setup.py` symlinks each skill directory that has a `SKILL.md` into
  `~/.claude/skills/<name>` (`validate_entry` `:812-817`, `link_one` `:1265-1295`). `_shared` has no
  `SKILL.md`, so it is never linked. It is reached only because the symlinked skill's real path sits
  next to it in the checkout. A copy install breaks it, and
  `skills/ai-kit-project-rules-agents/SKILL.md:31` already documents that.
- The spec family's real shared library today is not `_shared`. It is
  `skills/ai-kit-spec-review/ai_kit_spec` plus `ai-kit-spec.py` and `references/cross-ai.mjs`,
  reached by the sibling-directory rule:
  - spec-config calls `ai-kit-spec.py` (`SKILL.md:30-36`);
  - the superpowers shim does `sys.path.insert(0, <parent>/ai-kit-spec-review)`
    (`ai-kit-spec-superpowers.py:12-13`);
  - the GSD shim and `ai-kit-session-wake` do the same.
- spec-config has no scripts that others reuse. It is a pure consumer of ai-kit-spec-review's
  scripts. Moving "the common scripts" into spec-config or `_shared` therefore means moving
  `ai_kit_spec` (config_io, detection, routing, quota, execute_selection, runner_dispatch and the
  runner template) out of ai-kit-spec-review. Every shim's `sys.path` line, `pyproject.toml:55`,
  the pre-commit and pyright paths, and the tests' path setup would follow.
- Either target has the same weakness: backlog 999.14 (copy installs) breaks any cross-directory
  import, whether to `_shared` or to a sibling. A copy-installed skill then has to bundle its
  dependencies, or the installer has to copy `_shared` too.

## 5. Removing `skills/ai-kit-opencode-providers/`

What it is:
- about 1,000 lines: `jsonc_edit.py` 513, `cli.py` 195, `cross_reference.py` 177,
  `atomic_write.py` 62, `config_paths.py` 47;
- its test is `tests/test_ai_kit_opencode_providers.py` (1,307 lines);
- no other code imports it.

What a removal touches:
- `tests/test_ai_kit_opencode_providers.py`: delete it.
- The hard-coded unit test lists: `Makefile:12` (comment list), `.pre-commit-config.yaml:14` and
  `:59` (the unittest hook entry names `tests.test_ai_kit_opencode_providers`).
- `tests/test_gate_scope.py:39`: the frozen ruff file regex `PRE_WIDEN_RUFF_FILES` names the path.
  The live `.pre-commit-config.yaml` `files:` patterns do not (checked: the only hits there are the
  test-module names).
- `pyproject.toml:112`: pyright `extraPaths` entry.
- `tests/test_ai_kit_spec_runtimes_table.py:813`: its SKILL.md is in the `REWRITTEN` list that is
  checked for forbidden tokens.
- `README.md:40`: the skills table row.
- The installer needs no code change. `prune_stale` / `apply_stale_prune` (`tools/setup.py:1367-1377`)
  should remove the live `~/.claude/skills/ai-kit-opencode-providers` symlink once its target is
  gone. That needs a live check on the next install.
- Comment-only mentions that would point at a deleted file: `tools/config_doctor_readers.py:89,109,123,140`,
  `tools/config_doctor_appliers.py:28,146`, `tools/setup.py:1880`,
  `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py:6`, `raw_store.py:34`.
- History documents only: `docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md`,
  `.planning/intel/requirements.md`, the 2026-10-13 audit files, `docs/superpowers/plans/`, and 75
  archived files under `.planning/milestones/`. Leave the archives alone.
- The skill also appears in this session's available-skills list and would disappear from hosts
  after the re-link.

Which pieces to keep, and where:
- **JSONC scanner and surgical editor** (`jsonc_edit.py`: `_classify`, `_skip_insignificant`,
  `strip_jsonc_comments`, key insert/remove). It has already been copied twice by hand:
  - `tools/config_doctor_readers.py:106` (`strip_jsonc_comments`, `read_jsonc_checked`);
  - `tools/config_doctor_appliers.py:230-375` (`_skip_insignificant`, `set_jsonc_value`);
  - plus `tools/config_doctor_checks.py:232` (`_parse_jsonc_text`) and `tools/setup.py:80`
    (`_jsonc_reader`).

  The config doctor copy is the most complete living one, because it can set values. The removal
  is safe for the doctor: it never imported the skill. If spec-config later needs to read
  opencode.jsonc (for example the router-env provider block, for discovery), it should get the
  scanner from one shared module, not a fourth copy. Today nothing in `ai_kit_spec` reads
  opencode.jsonc (only `detection.py` comments mention `opencode.json`). The listing comes from the
  CLI.
- **Atomic writer** (`atomic_write.write_preserving_mode`). Separate copies exist in:
  - `tools/setup.py:1877` (`_atomic_write_json`, the one AGENTS.md names);
  - `tools/config_doctor_appliers.py:23,109`;
  - `ai-kit-usage-metrics` `raw_store.py:30` and `dashboard.py:2000`;
  - `ai-kit-session-wake/state.py:75`;
  - `jev-fast-decision/scripts/eval_cases.py:176`.

  `ai_kit_spec.config_io` writes the TOML through `render-toml`. Losing the skill's copy loses
  nothing. A shared spec-family helper only makes sense together with moving `ai_kit_spec`.
- **Path helpers** (`config_paths.py`). The opencode config path rule
  (`OPENCODE_CONFIG_DIR`, then `XDG_CONFIG_HOME`, then `~/.config`) is duplicated in
  `tools/config_doctor_checks.py:111`. The review-spec local and global paths duplicate
  `config_io.cfg_local_path` and `cfg_config_base` (`config_io.py:263-268`). The catalog path
  duplicates `ai_kit_spec.model_catalog.cache_catalog_path`. Nothing is lost; the spec copies are
  the ones to keep.
- **Cross-reference scan** (`cross_reference.py`: which TOML entries and catalog rows name a
  provider before it is removed). This is the only behaviour no other code has. It fits a
  spec-config "stale entry" check, which would have caught `router-env/my-plan-review`. A rewrite
  against `cfg_resolve` plus the live model listing beats porting the file.
- **List/remove a provider in opencode.jsonc**: no other code does this. The wish says it is
  unused. Removing a provider block is a config-doctor style job, if anyone wants it later.

## 6. Todos, backlog and next-milestone inputs that cover or contradict the wishes

Already covered:
- `NEXT-MILESTONE-INPUTS.md` Round 2 (`:436-472`, not yet committed: the working tree shows the
  file as modified) records these exact wishes: hub chaining, failing clearly, `_shared` or
  spec-config, removing opencode-providers, router-env defaults, the no-router defaults, and
  deferring GSD.
- Todo `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`:
  separate review and execute roles, effort per model checked first, runtime escalation as an
  opt-in flag that is off by default, model escalation as a separate flag. Round 1 in the inputs
  (`:345-347`) already records the owner decision that both are opt-in flags, with "never switch"
  kept as the default.
- Round 1 "Provider/model discovery" (`:410-422`): one shared discovery path, shared config
  paths, JSONC scanner and atomic writer; plan it together with 999.14.
- Backlog 999.17 (`ROADMAP.md:394-416`): `my-coding-lite` vs `my-coding` vs a named model through
  jev, in all three execute skills. It overlaps with "my-coding* optional, native as alternative".
  It is scoped to `-gsd` as well, and the wish defers GSD.

In tension or contradiction:
- **"Fail clearly when spec-config or its scripts are missing"** contradicts spec-review's current
  rule "never block the review over it", which degrades silently to the session default
  (`cross-ai-dispatch.md:52-54`). It also goes beyond the missing-TOML case, which today falls back
  to the session default (review) or ends in an empty stop (superpowers). Changing this reverses a
  deliberate design, so the owner has to say whether `--no-cross-ai` still means "session default,
  no config needed".
- **Three referees**: the inputs (`:432-434`) list as an open conflict "three referees in parallel
  through opencode vs one and two through pi, three only as a replacement". The Round 2 wish (one
  required, two desirable, three only as a pivot) settles the review half. Today
  `.planning/config.json:55-63` declares all three as GSD review lanes, which matches neither
  reading until GSD review is revisited. GSD is deferred, so it can stay for now. The memory note
  "Reviewers: one+two, three as fallback" agrees with the wish.
- **Execute fallback**: the wish says "a native model is an alternative" for execution. Superpowers
  execute has no session-default fallback today (section 1), and the native route only exists for
  Claude Code aliases or the session default (`SKILL.md:239-247`). A native fallback for execute is
  new behaviour, not a config change.
- **Backlog 999.14 (copy installs)**: the next feature after v1.3. It breaks `_shared` and every
  sibling import (`ai_kit_spec` from three skills). Choosing `_shared` as the home for common
  scripts makes 999.14 harder unless the installer copies `_shared` as well.
- **Backlog 999.15 (cross-AI chain skill)** keeps "never switch harness, provider or model" as the
  retry ladder. That is now only the default, with opt-in escalation (Round 1 decision). 999.15's
  text needs that note.
- **Refactor todo `2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`**: SJ-2
  (execute-superpowers refactor, collapse the resume paths) is deferred by the owner, but 999.17
  and this hub wish both change execute-superpowers. Any spec-config chain inserted into
  superpowers Step 2 lands on the resume paths SJ-2 wants to simplify. Order: SJ-2 first, or do
  both together.
- **The superpowers SKILL.md NEVER rule** "Never switch harness, provider or model"
  (`SKILL.md:31-33`) and the pre-dispatch ladder walk stay valid as the default. They need an
  explicit carve-out once the escalation flags exist.
- No todo covers "discovery across copilot CLI, cursor-agent, pi, opencode, claude" beyond what
  `detection.py`'s `RUNTIMES` table already does. That table already lists copilot and pi, among
  others. The Round 2 wish is the first record.

---
Not checked: whether `prune_stale` removes the opencode-providers link on a real re-install; copilot and cursor-agent router-env visibility (only opencode and pi were listed).
Risk: superpowers execute with no TOML ends in an empty `quota_exhausted` stop that never mentions
spec-config, which is the first thing the hub chain should fix.
