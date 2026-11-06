# Phase 31: Removals and small defects — Specification

**Created:** 2026-11-03
**Ambiguity score:** 0.12 (gate: ≤ 0.20)
**Requirements:** 15 locked

## Goal

`ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers` and `mermaid-audit` are gone from the tree with
every reference, nothing recommends, installs or wires rtk, and the seven known small defects are fixed, each
with a regression test. The baseline re-judge (Phase 32) and the later vendor phases then see only kept skills.

## Background

Live checks on 2026-11-03 (scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`, scripts in `tmp/p31/`):

- **References.** The three skills are named in `README.md`, `Makefile:12` (comment list), `.pre-commit-config.yaml`
  lines 14 and 59 (a hidden file a plain search skips), `pyproject.toml` (pyright `extraPaths` 112, 123, 132,
  136), `tests/test_gate_scope.py:38-39`, `tests/test_arch.py:782, 786, 1799` and the text-pin lists of
  `tests/test_ai_kit_spec_runtimes_table.py`, `tests/test_quota_policy_text.py` and
  `tests/test_cross_ai_skill_text.py`. Six test modules besides the adapter's own import `ai_kit_spec_gsd`:
  `test_ai_kit_spec_trust`, `test_ai_kit_spec_legacy_config`, `test_cross_ai_runner_e2e`,
  `test_ai_kit_spec_e2e`, `test_arch` and `test_ai_kit_spec_gsd` (removed). `tests/test_ai_kit_spec_gsd_tools.py`
  tests the kept `ai_kit_spec/gsd_tools.py` (curated-config loads it in five places); only its `prior_value` and
  execute-gsd SKILL.md cases go. No kept runtime code imports any of the three skills; markdown-to-pdf's
  `render_mermaid.py`, superpowers, session-wake, `tools/config_doctor_*`, `tools/setup.py` and usage-metrics
  name them only in comments or docstrings.
- **Code only the adapter used.** `runner_dispatch.project_runner_command(guidance=True)` and
  `PROJECT_GUIDANCE_PATH` (called only from `ai_kit_spec_gsd/gsd_cross_ai.py`); curated-config's guidance writer
  in `cross_ai_script.py` (`GUIDANCE_PATH`, `GUIDANCE_HEADER_RE`, `plan_guidance`, `_guidance_step`, the
  guidance argument of `ensure_runner`) and `cli.py` (`--guidance-file`), called only from execute-gsd's
  `references/cross-ai-hook-setup.md`; `gsd_tools.prior_value` (called only from `ai_kit_spec_gsd/gsd_config.py`).
  The runner template's own `--prepend-file` / `--no-preamble` flags are generic and stay (review dispatch uses
  `--no-preamble`). This repo's `.planning/config.json` `cross_ai_command` does not use the guidance file.
- **Stale links.** Dead ai-kit links (target removed from the kit) under the claude, pi, `.agents` and opencode
  skills dirs all survived `install --headless`, with and without `--skills all`. Only the wizard prunes (claude
  and pi roots); `prune_stale`, whose docstring promises the headless auto-remove, has no caller.
- **opencode 2.x.** The v2 migration guide renames the config's `provider` map to `providers` (`npm` →
  `package` with an `aisdk:` prefix, `api` → `settings.baseURL`) and keeps supported v1 fields working, normalized
  in memory; file locations are unchanged (`~/.config/opencode/opencode.json(c)`, project files). Live on opencode
  2.0.31, `opencode models --standalone` (a private server, so the owner's background service is untouched) in a
  scratch HOME listed a custom provider from a v1-shaped `provider` block and from a v2-shaped `providers` block,
  20 `anthropic/` models from an environment key (placeholder value) and 10 keyless `opencode/` models with no
  config. Login-based providers (`auth.json`) were not tested (no real login used). spec-config's
  `detect_opencode_models` runs plain `opencode models`, which uses the background service.
- **rtk.** Outside the history folders rtk appears in `AGENTS.md` (Tools and Stack), `README.md` (skills table,
  the session-start hook paragraph, the config doctor paragraph), house rule R05 (`rules.py`) and its SKILL.md,
  `tool_presence.py`, the config doctor's `rtk-cursor-integration` row and reader, usage-metrics (a capture
  source, the `rtk` runtime value, five `rtk_*` columns, two dashboard cases) and their tests.
  `tests/test_tool_substitution_hook.py::test_no_hook_file_mentions_the_rewrite_tool` already bans it in
  `tools/hooks/`.
- **Defects** (from `.planning/todos/pending/2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`,
  the v1.3 audit and `.planning/milestones/NEXT-MILESTONE-INPUTS.md`), each reproduced:
  - pi's missing skills: in a scratch HOME pi's own loader sees `ai-kit-cross-ai`, `ai-kit-session-wake` and
    `jev-fast-decision` after install. The miss reproduces through two causes. (1) `_is_inside` in `tools/setup.py`
    compares link targets with the kit dir as strings, so a link made through one spelling of the folder (this
    machine: `/home` resolves to `/var/home`, `tools/install.sh` passes `pwd -P`) is "foreign" to a run through
    another spelling: 28 linked, then 0 linked and 25 foreign-skipped, and pi's loader saw no skills.
    (2) `python3 tools/setup.py` run from a checkout without `AI_KIT_DIR` targets `~/.local/share/ai-kit` (the
    one-line installer's clone), so links into the checkout are foreign too.
  - pi's variables: pi 1.3.0 documents `PI_SESSION_ID`, `PI_SESSION_FILE`, `PI_PROVIDER`, `PI_MODEL` and
    `PI_REASONING_LEVEL` (added in 0.82.0), set only for commands the model runs through its own bash tool
    (`dist/core/tools/bash.js` deletes them, then sets them when a session context exists); `!` commands and RPC
    bash commands never get them. pi's own code, run in a scratch HOME with no model call, confirmed both paths.
    The "they do not exist" claim (`.planning/milestones/v1.3-OWNER-FOLLOWUP.md:72`, copied into
    `NEXT-MILESTONE-INPUTS.md:81` and the todo) came from a herdr/RPC session that used the second path.
    curated-config's inventory reads `PI_PROVIDER` (`inventory.py:472`, SKILL.md line 134); the Phase 22 guide
    (`22-INTERACTIVE-PI.md` S2) expects the variables without saying which path sets them.
  - `edge_floor.py check` on the 25.1 SPEC: `ok:false`, floor 48, table 47, missing `encoding R9`. Five more
    archived v1.3 SPECs fail (17, 18, 18.1, 21, 24); they stay history.
  - goal-prompt `_gsd_json` calls `json.loads(out)` directly; gsd-core prints `@file:<path>` for a JSON result
    over 50 KB (`resolveAtFileOutput` in `bin/lib/io.cjs`), which then fails as "did not print JSON". No ai-kit
    Python handles `@file:` today.
  - `ai_kit_spec/routing.py` `host_can_select` docstring: "until Phases 20-22"; only claude has native selectors.
  - Hand-copied runtime lists with no drift test against `RUNTIMES`: curated-config `cross_ai.RUNNER_IDS` (a
    deliberate subset), `host.HOSTS`, goal-prompt `gp_host.HOST_BINARY` (cursor → `agent`), the plan-editor error
    text naming the runner ids (`plan_edit.py:374`); the JS template list is tested only as a superset
    (`assertLessEqual` in `test_ai_kit_spec_runtimes_table.py`).
  - `AGENTS.md:122` links `.claude/cli-environment.md`, which `.gitignore:8` (`.claude/`) ignores.

## Requirements

1. **execute-gsd removed, GSD plans go to `/gsd-execute-phase`**: `skills/ai-kit-spec-execute-gsd/` and every reference to it are gone, and the execute router hands GSD plans to `/gsd-execute-phase`.
   - Current: the skill, `tests/test_ai_kit_spec_gsd.py`, adapter cases in six other test modules, test-list entries in `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`, `tests/test_gate_scope.py` and `tests/test_arch.py`, the README row and mentions in curated-config, superpowers, session-wake, spec-review and the router's SKILL.md; the router delegates `gsd` to the adapter.
   - Target: the folder and its own test module are deleted; the other test modules lose only the adapter cases, and a shared-module behaviour those cases covered keeps at least one test through a kept caller; every list and doc entry is removed; `ai-kit-spec-execute`'s description and its `gsd` branch name `/gsd-execute-phase`; `detect_framework.py` still reports `gsd`.
   - Acceptance: a tracked-file search for `ai-kit-spec-execute-gsd`, `ai_kit_spec_gsd` and `ai-kit-spec-gsd.py` outside the history folders finds nothing; `make test` passes; a test pins that the router's `gsd` branch names `/gsd-execute-phase` and no adapter.

2. **Code only the adapter used is removed**: the runner guidance prepend, `PROJECT_GUIDANCE_PATH`, curated-config's guidance writer and `gsd_tools.prior_value` are gone.
   - Current: `project_runner_command(spec, guidance=True)` adds `--no-preamble --prepend-file .planning/scripts/cross-ai-guidance.md`; curated-config `ensure-runner --guidance-file` writes that file; `prior_value` parses `config-set` output; each has tests.
   - Target: `project_runner_command` has no guidance parameter; `PROJECT_GUIDANCE_PATH`, curated-config's `GUIDANCE_PATH`, `GUIDANCE_HEADER_RE`, `plan_guidance`, the guidance step and `--guidance-file` are deleted with their tests and doc lines (curated-config SKILL.md, `references/runner.md`); `ensure-runner` output keeps its other keys; `prior_value` and its tests go. The runner template and its flags are unchanged. Projects whose `cross_ai_command` already names the guidance file are not migrated; the file stays where it is and keeps working.
   - Acceptance: a search for `PROJECT_GUIDANCE_PATH`, `guidance=True`, `--guidance-file`, `cross-ai-guidance.md` and `prior_value` in `skills/`, `tools/` and `tests/` finds nothing; `ensure-runner --cwd <scratch>` still renders the runner and reports `ready`; the template's version stamp is unchanged.

3. **opencode-providers removed**: `skills/ai-kit-opencode-providers/` and every reference to it are gone.
   - Current: the skill (about 1,000 lines), `tests/test_ai_kit_opencode_providers.py`, list entries in `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`, `tests/test_gate_scope.py`, `tests/test_ai_kit_spec_runtimes_table.py`, the README row and origin comments in `tools/config_doctor_readers.py`, `tools/config_doctor_appliers.py`, `tools/setup.py` and usage-metrics `paths.py` / `raw_store.py`.
   - Target: the folder and its test are deleted; list entries and the README row are removed; each origin comment is reworded so it names no deleted file.
   - Acceptance: a tracked-file search for `ai-kit-opencode-providers` and `ai_kit_opencode_providers` outside the history folders finds nothing; `make test` passes.

4. **mermaid-audit removed, markdown-to-pdf kept**: `skills/mermaid-audit/` and every reference to it are gone; markdown-to-pdf keeps rendering Mermaid through `mmdc`.
   - Current: the skill, `tests/test_mermaid_style.py`, list entries in `Makefile`, `.pre-commit-config.yaml` and `pyproject.toml`, the README row, and `render_mermaid.py`'s docstring naming it as origin.
   - Target: the folder and its test are deleted; entries and the README row removed; `render_mermaid.py`'s docstring names no deleted file; markdown-to-pdf's code and tests are otherwise unchanged, and its real-render test keeps Phase 28 D-09's named skip under a scratch HOME.
   - Acceptance: a tracked-file search for `mermaid-audit`, `mermaid_audit` and `test_mermaid_style` outside the history folders finds nothing; `tests/test_markdown_to_pdf.py` passes.

5. **spec-config reports stale opencode providers**: spec-config's detection step lists every configured reference to an opencode provider that opencode no longer serves, as non-blocking warnings, in normal setup and under `--check-only`.
   - Current: only the removed providers skill warned, and only while removing a provider; spec-config has no such report.
   - Target: the references scanned are the removed skill's three sources in its order: local `./.aikit/review-spec.toml`, global `${XDG_CONFIG_HOME:-~/.config}/ai-kit/review-spec.toml` (a hit marked inactive when the local file sets `strategy = "local-only"`), and the cached model catalog (`_meta` skipped). A reference is an opencode reviewer's `provider/model` model id or a catalog entry's provider. The served providers come from `opencode models` (labelled "listed by opencode"); when that cannot run, from the `provider` and `providers` keys of the opencode config files, read-only through a small JSONC reader (labelled "config file only; login and environment providers not checked"); when neither is available, the report says "not checked" with the reason. Each source prints scanned, scanned-inactive or absent; each warning names the file, the reviewer or catalog key and the provider. Never reads `auth.json`; never prints a key or an `apiKey` value; never blocks or edits anything.
   - Acceptance: tests with fake `opencode models` output and synthetic config files cover a stale reviewer, a stale catalog entry, an inactive global hit, a v1-shaped and a v2-shaped config, the config fallback label, the "not checked" case and a served provider producing no warning; the JSONC reader has a drift test against `tools/config_doctor_readers.py`'s scanner on shared fixtures; a fixture holding an `apiKey` never shows it in output.

6. **Installs prune dead ai-kit links**: every install, interactive or not, removes ai-kit links under the claude and pi skills roots whose target no longer exists in the kit, with one warning per link.
   - Current: only the wizard prunes, after a confirm; `install --headless` leaves dead links in place.
   - Target: the non-interactive install wires `prune_stale`'s documented behaviour for the claude root and the pi root (when the pi dir exists): each dead ai-kit link is removed and one `warn: removing dead ai-kit link <cat>/<name> (entry removed upstream)` line is printed; foreign links, real files and live links are never touched; the wizard keeps its confirm.
   - Acceptance: a scratch-HOME test seeds dead links for the three removed skill names in both roots, runs `install --headless` (with and without `--skills`), and finds them gone with one warning each, while a foreign link, a real directory and a live ai-kit link at neighbouring names survive.

7. **rtk is not recommended, installed or wired anywhere**: no tool list, guidance text, house rule, config-doctor row, AGENTS.md section or README text recommends, installs or wires rtk, and a test enforces it.
   - Current: rtk appears in the places listed in Background; house rule R05 tells agents how its rewriting works; the config doctor checks and recommends `rtk init -g --agent cursor`.
   - Target: AGENTS.md and README lose their rtk text; house rule R05 is retired and its id stays unused (rules keep their ids; the ruleset is 19 rules and every "20-rule" text says 19); `tool_presence.py` drops its `rtk` key; the config doctor's `rtk-cursor-integration` row and `probe_rtk_cursor_hook` go. usage-metrics keeps reading rtk data that already exists (capture source, columns and dashboard cases stay, as optional input) and its SKILL.md never tells the agent to install or run rtk; nothing deletes stored data. A new test fails on a case-insensitive whole-word `rtk` in any tracked file outside its named exemptions, each listed in the test with its reason: `.planning/`, `docs/prds/`, `docs/superpowers/` (history), the test itself (it names the pattern), `skills/ai-kit-usage-metrics/` and `tests/test_ai_kit_usage_metrics.py` (they read existing rtk history and do not use rtk). It replaces the hooks-only ban.
   - Acceptance: the new test passes on the tree and fails on a synthetic tracked file outside the exemptions that names rtk (non-vacuity case); the house-rules checker reports no R05 and still reports R06; the config doctor's catalog has no rtk row; a usage-metrics run over a scratch rtk `history.db` still captures and refines its rows, and a run with none succeeds.

8. **The installer finds its kit and its links by resolved paths**: `tools/setup.py` and `tools/install.sh` treat any spelling of the same folder as the same folder, and a checkout run uses its own checkout, so pi gets its skills.
   - Current: `_is_inside` compares strings, so an alias spelling makes ai-kit's own links "foreign" and pi gets none; `setup.py` run from a checkout without `AI_KIT_DIR` uses `~/.local/share/ai-kit`.
   - Target: the home is found through `$HOME` (`os.path.expanduser("~")` in Python), never a hardcoded root; link targets and the kit dir are compared after resolving both (`os.path.realpath`; `pwd -P` / `readlink -f` in shell); `setup.py` uses the checkout that holds the running script unless `AI_KIT_DIR` is set; `~/.local/share/ai-kit` stays the default only for the one-line installer's own clone.
   - Acceptance: scratch-HOME tests with a synthetic symlinked alias of the home and of the kit dir install, re-install through the other spelling and find 0 foreign-skipped and the three pi skills linked; a `setup.py` run from a scratch checkout copy without `AI_KIT_DIR` links into that copy; `bash tests/test_install.sh` and the installer e2e pass unchanged in what they assert for the one-line install.

9. **pi's session variables are described as they really work**: curated-config says `PI_PROVIDER` and `PI_MODEL` exist only in commands the pi agent runs through its own bash tool.
   - Current: SKILL.md line 134 and inventory's "PI_PROVIDER is unset; run inventory inside the pi session" message do not name the path; the archived Phase 22 guide and the v1.3 follow-up file record the variables as nonexistent or expected without the path.
   - Target: curated-config's SKILL.md and inventory's message say the variables are set for the pi agent's own bash-tool commands, not for `!` commands or RPC bash; the archived guide and `v1.3-OWNER-FOLLOWUP.md` get a dated correction note; a doc-contract test pins the wording.
   - Acceptance: the doc-contract test passes; the verification records a live check: in a herdr pane the pi agent is asked to run `env | grep '^PI_'` through its own bash tool and its answer, names only, shows `PI_PROVIDER` and `PI_MODEL` (scratch HOME where pi allows it; no credential is copied).

10. **The 25.1 edge floor is fixed and current SPECs are guarded**: the Phase 25.1 SPEC passes `edge_floor.py check`, and a test fails when a current-milestone SPEC drifts from its floor.
    - Current: 25.1 fails (missing `encoding R9`); no test runs the engine on committed SPECs.
    - Target: 25.1's Edge Coverage gains the missing row marked `(added …)`; a test runs `edge_floor.py check` on every SPEC under `.planning/phases/` (the current milestone) and skips with a named reason when node or the engine is missing; the five other failing archived SPECs stay as they are, recorded as history.
    - Acceptance: `edge_floor.py check` on 25.1 returns `ok:true`; the new test passes on the tree and fails on a fixture SPEC with a row removed.
    - *(amended 2026-11-06, planning: no test may read `.planning/` (`tests/test_arch.py` `check_no_planning_reader`, no exceptions), so the guard over the committed SPECs runs in `make check-dogfood` (`tools/check_dogfood.py`, part of `make validate` and a pre-push hook), and its logic is unit-tested on fixture SPECs, including the row-removed failing fixture and the named skip; a SPEC with no Edge Coverage section yet is a named note, not a failure; the 30.1 SPEC, which fails the engine by one row (`encoding R3`), gets that row in the same change. Planning ruling the owner may override.)*

11. **goal-prompt detect reads gsd-core's `@file:` output**: every gsd-tools query goal-prompt parses accepts an `@file:<path>` reply.
    - Current: `_gsd_json` runs `json.loads` on the raw stdout, so a large roadmap fails as "did not print JSON".
    - Target: a reply starting `@file:` is read from that path before parsing, the way gsd-core's `resolveAtFileOutput` does; a missing or unreadable file is the same failure as bad JSON; any other goal-prompt parse of gsd-tools output uses the same helper.
    - Acceptance: tests with a fake gsd command that prints `@file:<scratch json>` get the parsed roadmap; one pointing at a missing file gets the existing error.

12. **The routing docstring states today's behaviour**: `host_can_select`'s docstring names no phase.
    - Current: "Every other host is session-default-only until Phases 20-22 (R3)."
    - Target: it says per-call selection is verified only for runtimes with native selectors in `RUNTIMES` (today claude) and every other host is session-default-only.
    - Acceptance: a test asserts the docstring contains no "Phase" and that the runtimes with native selectors are exactly the ones it names.

13. **Hand-copied runtime lists are tied to the runtime table**: one drift test compares every hand-copied runtime list with `RUNTIMES`.
    - Current: `RUNNER_IDS`, `host.HOSTS`, `HOST_BINARY` and the plan-editor error text have no comparison; the JS template list is checked only as a superset.
    - Target: one test compares each list with `RUNTIMES` (ids and, for `HOST_BINARY`, binaries), with each deliberate difference listed with its reason (for example `RUNNER_IDS` excluding claude); the plan-editor error text is built from `RUNNER_IDS`; the JS template list is compared for equality, not superset.
    - Acceptance: the test passes on the tree and fails when a synthetic runtime is added to a copy only.

14. **AGENTS.md links no gitignored file**: AGENTS.md has no link to `.claude/cli-environment.md`, and a test fails on any AGENTS.md link to an ignored or missing file.
    - Current: `AGENTS.md:122` links the ignored file.
    - Target: the paragraph is rewritten without rtk and without the link, keeping a one-line note on the modern CLI tools and graphify; a test resolves every relative link in AGENTS.md and fails on a missing target or one `git check-ignore` reports.
    - Acceptance: the test passes on the tree and fails on a fixture AGENTS.md linking an ignored file.

15. **Changed skills meet the judge bar (JDG-04)**: every SKILL.md this phase materially changes passes the judge loop.
    - Current: `ai-kit-spec-execute`, `ai-kit-spec-config`, `ai-kit-gsd-curated-config` and `ai-kit-project-rules-agents` change materially here; usage-metrics' SKILL.md changes only if its wording must.
    - Target: each changed SKILL.md has new-shape evals and tests, no critical or high finding or grade B or better, and no regression beyond judge variation, recorded in this phase's verification.
    - Acceptance: `31-VERIFICATION.md` lists each changed skill with its judge result and the evals and tests it carries.

## Boundaries

**In scope:**
- Deleting the three skills, their tests and every list, doc and comment entry (R1, R3, R4).
- Removing the code only execute-gsd used (R2).
- spec-config's stale opencode provider report, its config fallback and JSONC reader (R5).
- Dead-link pruning in non-interactive installs, claude and pi roots (R6).
- The rtk ban and its test, R05 retired, the doctor row removed (R7).
- The seven defects with their tests (R8-R14).
- The judge bar for changed skills (R15).

**Out of scope:**
- The runner template (`cross-ai.mjs`) and its `--prepend-file` / `--no-preamble` flags — generic, used by review.
- Migrating projects whose `cross_ai_command` names the guidance file — no migration (owner, 2026-11-03).
- Deleting rtk data the owner already stored, or the usage-metrics rtk reader — reading history stays.
- Repairing the five other archived SPECs whose floors drift (17, 18, 18.1, 21, 24) — history.
- Stale models and providers on hosts other than opencode, adding `--standalone` to spec-config's opencode listing, and matching the opencode profile and runner comments to 2.x `--help` — Phase 35 (its criteria 3 and 4 build on R5).
- Pruning links under `.agents/skills` or opencode skills dirs — ai-kit links only the claude and pi roots.
- The other todo items (runner error-catalogue rows, the Claude stdout matcher, the session-wake notices, the StopFailure capture) — not in DEF-01.
- The path-length goal-prompt test and the no-git e2e test — Phase 28 (GATE-03).

## Constraints

- Runtime code stays stdlib-only; the JSONC reader in spec-review is hand-rolled and read-only (no parser dependency).
- Tests use scratch HOMEs and synthetic files; fakes replace host CLIs (Phase 28's tripwire PATH and fake helper),
  so tests never run the real `opencode` or `pi`.
- Path tests model aliases with a synthetic symlinked home and kit dir inside the scratch HOME; this machine's real
  paths never appear in source or tests. The same model covers macOS, where `/Users` and `/var` / `/tmp` resolve
  through `/private` symlinks.
- No hardcoded absolute path in source, tests or assets; the home comes from `$HOME`.
- Installer writes stay atomic where they touch config; link removal touches only links whose target lies inside
  the resolved kit dir.
- Deletions follow the logical-commit rule: each removal lands with its tests and docs.

## Acceptance Criteria

- [ ] Tracked-file searches outside `.planning/`, `docs/prds/` and `docs/superpowers/` find no name of the three removed skills. *(amended 2026-11-06, planning: `tests/fixtures/archived/` (byte copies of archived planning data, pinned by an arch rule) also counts as history for these searches; the package name is matched as a whole word (`ai_kit_spec_gsd\b`), so the kept `tests/test_ai_kit_spec_gsd_tools.py` does not match. Planning ruling the owner may override.)*
- [ ] The execute router sends a GSD plan to `/gsd-execute-phase` (pinned by a test).
- [ ] No guidance prepend, `PROJECT_GUIDANCE_PATH`, `--guidance-file` or `prior_value` remains; the runner template is unchanged.
- [ ] spec-config prints the stale-provider warnings with the right source label in both run modes, never a key.
- [ ] A headless install in a scratch HOME removes dead ai-kit links in the claude and pi roots, one warning each, and nothing else.
- [ ] The rtk-mention test passes on the tree, fails on its non-vacuity case, and lists each exemption with its reason.
- [ ] House rule R05 is retired with its id unused; the doctor has no rtk row; usage-metrics still reads existing rtk data.
- [ ] An alias-spelled re-install finds 0 foreign links and links the three pi skills; a checkout run links into that checkout; `tests/test_install.sh` passes.
- [ ] curated-config's pi variable wording is pinned; the herdr live check is recorded in the verification.
- [ ] 25.1 passes `edge_floor.py check`; the current-milestone SPEC guard runs in the suite.
- [ ] goal-prompt detect parses an `@file:` reply.
- [ ] The routing docstring names no phase; the runtime-list drift test passes and fails on a copy-only runtime.
- [ ] AGENTS.md has no link to an ignored or missing file, enforced by a test.
- [ ] Each materially changed SKILL.md meets the judge bar, recorded in `31-VERIFICATION.md`.
- [ ] `make test` and `make validate` pass.

## Edge Coverage

**Coverage:** 65/65 applicable edges resolved · 0 unresolved (65 engine rows, 0 added)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A name that contains a removed one as a prefix (`ai-kit-spec-execute`, `ai-kit-spec-execute-superpowers`) is kept; searches match the full removed names only |
| empty | R1 | ✅ covered | A test module left with no test after its adapter cases go is deleted and dropped from every list, never left empty |
| encoding | R1 | ✅ covered | Searches are plain ASCII and case-sensitive on the exact skill, package and script names |
| ordering | R1 | ✅ covered | Test-list entries are removed in place; the remaining lists keep their order |
| concurrency | R1 | ✅ covered | The parallel runner discovers modules from files, so a deleted module is never scheduled; no shared state |
| adjacency | R2 | ✅ covered | `--no-preamble` stays where review dispatch passes it without `--prepend-file`; only the guidance pair goes |
| empty | R2 | ✅ covered | `ensure-runner` without guidance (the only form left) still reports its other keys |
| encoding | R2 | ✅ covered | The runner template bytes and version stamp are unchanged, proven by the existing template pin |
| ordering | R2 | ✅ covered | `ensure-runner` output keeps its key order for callers that print it |
| concurrency | R2 | ✅ covered | Removing the guidance write leaves the runner write's mkstemp plus `os.replace` path as the only write |
| adjacency | R3 | ✅ covered | The JSONC scanner ported into `tools/` stays; only comments naming the deleted origin change |
| empty | R3 | ✅ covered | A tools module whose only mention was the origin comment keeps its code; the comment is reworded, never deleted with code |
| encoding | R3 | ✅ covered | Searches match both the hyphen and the underscore spellings |
| ordering | R3 | ✅ covered | List entries are removed in place; the remaining lists keep their order |
| concurrency | R3 | ✅ covered | Same as R1: module discovery from files, no shared state |
| adjacency | R4 | ✅ covered | markdown-to-pdf's `render_mermaid.py` keeps its code; only its docstring changes |
| empty | R4 | ✅ covered | Without `mmdc` or headless Chrome the real-render test skips with Phase 28 D-09's named reason |
| encoding | R4 | ✅ covered | Searches match `mermaid-audit`, `mermaid_audit` and `test_mermaid_style` |
| ordering | R4 | ✅ covered | `pyproject.toml` `extraPaths` keep their order after the two entries go |
| concurrency | R4 | ✅ covered | Same as R1: module discovery from files, no shared state |
| adjacency | R5 | ✅ covered | A reviewer whose provider id is also a runtime name (`opencode`) is matched on the model id's provider part only, never on the `runtime` field |
| empty | R5 | ✅ covered | No review-spec file, an empty catalog or no opencode reviewer prints the scanned or absent lines and no warning |
| encoding | R5 | 🧪 backstop | Provider ids are compared byte for byte as opencode prints them; a non-ASCII id in a fixture is reported unchanged (held-out edge test) |
| ordering | R5 | ✅ covered | Sources print in the fixed order local, global, catalog; warnings follow file order |
| concurrency | R5 | ✅ covered | The report reads each file once and writes nothing, so a concurrent edit gives the old or new view, never a partial write |
| adjacency | R6 | ✅ covered | A dead link next to a live ai-kit link, a foreign link or a real directory at neighbouring names: only the dead one goes |
| empty | R6 | ✅ covered | No dead links prints no warning; a missing pi dir is skipped with the existing note and never created |
| encoding | R6 | ✅ covered | Link names with spaces or non-ASCII characters are handled as path strings; the warning prints the name as stored |
| ordering | R6 | ✅ covered | Warnings print in sorted category/name order, claude root before pi root |
| concurrency | R6 | 🧪 backstop | A link that disappears between detection and removal is counted gone, not an error (held-out edge test) |
| adjacency | R7 | ✅ covered | Whole-word, case-insensitive match: `rtk` matches, `artkit`-style substrings do not |
| empty | R7 | ✅ covered | usage-metrics with no rtk `history.db` and no `tee/` captures nothing for rtk and succeeds |
| encoding | R7 | ✅ covered | The scan reads tracked files as UTF-8 with replacement and skips binary files |
| ordering | R7 | ✅ covered | Retired R05 leaves R04 and R06 in their places; reports list rules in id order with the gap |
| concurrency | R7 | ✅ covered | The test reads `git ls-files` once; no shared state |
| adjacency | R8 | ✅ covered | A kit dir that is a prefix of another folder's name (`ai-kit` vs `ai-kit-old`) is not "inside"; the check compares path components after resolving |
| empty | R8 | ✅ covered | An unset or empty `$HOME` fails the install with a message, never a guessed home |
| ordering | R8 | ✅ covered | `AI_KIT_DIR` wins over the running checkout, which wins over the default clone path |
| adjacency | R9 | ✅ covered | The wording names both paths side by side: set for the agent's bash tool, absent for `!` and RPC bash |
| empty | R9 | ✅ covered | With `PI_PROVIDER` unset, inventory keeps its plan-unset path and the new message |
| encoding | R9 | ✅ covered | The doc-contract test matches the exact variable names in ASCII |
| ordering | R9 | ✅ covered | The herdr live check runs after the wording lands and before verification closes |
| concurrency | R9 | ✅ covered | The variables are resolved per command by pi; no state is shared between checks |
| adjacency | R10 | ✅ covered | The added 25.1 row sits with R9's other rows and is marked `(added …)` |
| empty | R10 | ✅ covered | A phase folder with no SPEC is skipped; an engine failure (exit 2) is a named skip, not a pass |
| ordering | R10 | ✅ covered | The guard checks SPECs in sorted path order and reports each failing path |
| adjacency | R11 | ✅ covered | Output that merely contains `@file:` later in the text is not redirected; only a reply starting with it is |
| empty | R11 | ✅ covered | `@file:` with an empty path, or a missing file, gives the existing "did not print JSON" error |
| ordering | R11 | ✅ covered | The file is read before JSON parsing, the order gsd-core's `resolveAtFileOutput` uses |
| concurrency | R11 | ✅ covered | The temp file is read once; a file gsd-core removes later does not matter after the read |
| adjacency | R12 | ✅ covered | The docstring names the selector source (`RUNTIMES`) rather than repeating the runtime list |
| empty | R12 | ✅ covered | With no runtime having native selectors the sentence still holds (every host session-default-only) |
| encoding | R12 | ✅ covered | The test reads the docstring as text; plain ASCII |
| ordering | R12 | ✅ covered | The test compares sets, so table order does not matter |
| adjacency | R13 | ✅ covered | A deliberate subset (`RUNNER_IDS` without claude) passes only with its listed reason; an unlisted difference fails |
| empty | R13 | ✅ covered | An empty copy fails the test unless listed as deliberately empty |
| encoding | R13 | ✅ covered | Ids and binary names are compared as exact ASCII strings |
| ordering | R13 | ✅ covered | Lists are compared as sets; the plan-editor text is built from `RUNNER_IDS` in its own order |
| adjacency | R14 | ✅ covered | Links with an anchor (`file.md#part`) resolve the file part only |
| empty | R14 | ✅ covered | An AGENTS.md with no relative links passes |
| ordering | R14 | ✅ covered | The test reports every bad link, in file order, not only the first |
| concurrency | R14 | ✅ covered | `git check-ignore` reads the index and ignore files once per run; no writes |
| adjacency | R15 | ✅ covered | A skill changed only by a removed cross-reference line is judged too when the change touches its flow; the verification says which |
| empty | R15 | ✅ covered | A skill with no material change is listed as not judged, with the reason |
| ordering | R15 | ✅ covered | Judging runs after the skill's last change in the phase, so the recorded result is current |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT read `auth.json` or print any key or `apiKey` value in the stale-provider report | R5 | resolved | verification: test — a fixture config with an `apiKey` and a scratch `auth.json` with a marker value; output never contains either |
| MUST NOT remove a link, file or folder that is not an ai-kit link whose resolved target lies inside the resolved kit dir and no longer exists | R6, R8 | resolved | verification: test — foreign link, real directory and live link survive the prune in the scratch HOME |
| MUST NOT delete or rewrite the owner's stored usage data, or touch the owner's real host configs, in tests or agent steps | R7, R9 | resolved | verification: test — scratch `XDG_DATA_HOME` fixtures and Phase 28's real-home guard (`AI_KIT_REFUSE_REAL_HOME=1`); judgment for the herdr live check (scratch HOME, no copied credentials) |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Three removals, the rtk ban and seven defects, each with a test |
| Boundary Clarity   | 0.90  | 0.70 | ✓      | Phase 35 overlap, runner template and archived SPECs explicitly out |
| Constraint Clarity | 0.85  | 0.65 | ✓      | stdlib, scratch HOME, synthetic aliases, no hardcoded paths |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | Each requirement has a falsifiable test or search |
| **Ambiguity**      | 0.12  | ≤0.20| ✓      | Round 0: 0.30; round 1: 0.21 |

## Interview Log

Interactive, 2 rounds (the owner answered through the coordinator). In the interactive path the ladder screens
only items the owner asks it to; none were asked, so no backend was called. Rule: best design over the smallest
diff (`mvp-mode` inactive).

| Round | Perspective | Question summary | laya (advisory) | typesafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | How spec-config spots a stale opencode provider | – | – | `opencode models` first; research v2 config before any fallback (R5) |
| 1 | Boundary Keeper | Should non-interactive installs prune dead links? | – | – | Yes, claude and pi roots, one warning per link (R6) |
| 1 | Researcher | The "nonexistent pi variables" defect | – | – | Re-researched from scratch (round 2) |
| 1 | Simplifier | How far the edge-floor fix goes | – | – | 25.1 plus a current-milestone guard; archived SPECs stay history (R10) |
| 1 | Boundary Keeper | What counts as history for the rtk test; stored rtk data | – | – | Ban recommending, installing or wiring; usage-metrics keeps reading existing data; named exemptions; nothing deleted; RMV-04 amended (R7) |
| 1 | Seed Closer | House rule numbering; projects set up by the removed hook | – | – | R05 retired, id left unused; no migration (R7, R2) |
| 2 | Researcher | pi variables item | – | – | Kept, reworded: the variables exist only in the agent's own bash-tool commands; herdr live check in verification (R9) |
| 2 | Failure Analyst | Fallback when `opencode models` cannot run | – | – | Config file read-only through a small JSONC reader with a drift test, labelled "config file only; login and environment providers not checked" (R5) |
| 2 | Boundary Keeper | Where the stale-provider report appears | – | – | Detection step, normal setup and `--check-only`, non-blocking (R5) |
| 2 | Failure Analyst | How far the path fix goes | – | – | Both causes, portably: `$HOME`, resolved-path comparison, checkout runs use their checkout; DEF-01 amended (R8) |

---

*Phase: 31-removals-and-small-defects*
*Spec created: 2026-11-03*
*Next step: /gsd-discuss-phase 31 — implementation decisions (how to build what's specified above)*
