---
phase: 39-lane-capability-blocks-and-lens-skills
verified: 2026-11-23T20:40:00Z
verified_head: 4544493
status: passed
score: 12/12 requirements verified
covered_files: [".planning/phases/39-lane-capability-blocks-and-lens-skills/39-01-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-01-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-02-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-02-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-03-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-03-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-04-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-04-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-05-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-05-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-06-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-06-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-07-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-07-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-08-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-08-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-09-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-09-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-10-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-10-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-11-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-11-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-12-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-12-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-13-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-13-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-14-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-14-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-15-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-15-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-16-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-16-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-17-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-17-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-18-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-18-SUMMARY.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-19-PLAN.md", ".planning/phases/39-lane-capability-blocks-and-lens-skills/39-19-SUMMARY.md", "skills/ai-kit-cross-ai/SKILL.md", "skills/ai-kit-gsd-curated-config/SKILL.md", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py", "skills/ai-kit-spec-config/SKILL.md", "skills/ai-kit-spec-review/SKILL.md", "skills/ai-kit-spec-review/ai_kit_spec/capability_block.py", "skills/ai-kit-spec-review/ai_kit_spec/cli.py", "skills/ai-kit-spec-review/ai_kit_spec/config_io.py", "skills/ai-kit-spec-review/ai_kit_spec/config_status.py", "skills/ai-kit-spec-review/ai_kit_spec/edit_pass.py", "skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py", "skills/ai-kit-spec-review/ai_kit_spec/lens_delivery.py", "skills/ai-kit-spec-review/ai_kit_spec/prompt_guard.py", "skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py", "skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py", "skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py", "skills/ai-kit-spec-review/ai_kit_spec/skill_table.py", "skills/ai-kit-spec-review/references/cross-ai-selftest.mjs", "skills/ai-kit-spec-review/references/cross-ai.mjs", "skills/ai-kit-spec-review/references/skill-roles.json"]
covered_digest: "v4:sha256:a79e3482fd45e61cbd86e261f58848e3376872d444c8939512eabae04668c2ec"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 39: Lane capability blocks and lens skills, verification report

**Phase goal (ROADMAP):** Every review or execute lane is told exactly the tools and skills it can use, and lens skills present on
the machine reach reviewers.
**Verified:** 2026-11-23 at HEAD 4544493 (branch gsd/phase-39-lane-capability-blocks-and-lens-skills, clean tree).
**Status:** passed (12/12 SPEC requirements and all 5 roadmap criteria have code, a test and run evidence). The owner items below
are NOT verified and none is a SPEC acceptance condition.
**Re-verification:** No, initial verification. No `39-VALIDATION.md` exists, so none was written.

## Live proof: required by the SPEC or not

The D-18 live probe (does a read-only claude, opencode or pi lane read a lens file outside the repository) and the real-home
probes were not run (no consent line). The SPEC does not require them: R6's dated amendment says the spike "is not run in this run
... so every path form keeps its label and those hosts get prose", and R5/R6 acceptance is fixture-based ("with a fixture skills
root ..."). So this is **verified-by-fixture with the limit stated**: path delivery is verified only for pi (its own docs, 2026-11-16);
claude, copilot and cursor get the runner's prose block; `shell` stays `unknown` for claude, opencode, cursor and codex review;
the MCP seed arguments keep their `unverified` label. No status change for this, and no human_needed item.

## Goal achievement: SPEC requirements

Code is `path:line` of the delivering definition; test is the module and a test that fails without it. "Ran" = I ran it at 4544493.

| # | Requirement | Status | Code | Test (fails without it) |
|---|-------------|--------|------|-------------------------|
| R1 | One role-keyed table, rescanned every run; MCP names only; run-scoped MCP file (REV-05) | VERIFIED | `skill_table.py:16` (closed ROLES), `:245` `scan`, `:428` `mcp_names`, `:464` `skill_roots`; `references/skill-roles.json`; `lens_delivery.py:40,60` `mcp_pick`, `write_mcp_file` | `test_skill_table.py:63` roles locked across code and seed, `:269` seed row never makes presence, `:413` parallel scans equal, `:450` malformed MCP config is unknown for that host only, `test_lens_delivery.py:197,246` pick, file and runner applies it |
| R2 | Sorter proposes, owner confirms (REV-05) | VERIFIED | `skill_classify.py` (`classify-skills`, `confirm-skill-role`), `config_io.py` lock | `test_skill_table.py:802` seed and user-stated not offered; `test_config_role_write.py` (18 ran); review fix tests `test_confirm_skill_role_writes_same_entry`, `test_render_toml_cli_holds_the_lock` |
| R3 | Runner prints capabilities from the final argv (REV-04) | VERIFIED | `cross-ai.mjs:2168` `laneCapabilities`, `:2147` `toolListCaps`, printed `:7114` | `test_runner_skills_argv.py:275` fixture table (`runner_capabilities.json`), self-test cap cases in `cross-ai-selftest.mjs:167`; `test_capability_block.py:283` fixture matrix |
| R4 | Capability block per lane from those facts (REV-04) | VERIFIED | `capability_block.py` composer; wired in `reviewer_dispatch.py` and `execute_dispatch.py` | `test_capability_block.py:62` pi review golden, `:158` no cbm line when binary missing on child PATH, `:167` child PATH not parent, `:217` pi has no shell tool, `:226` unknown block |
| R5 | Lens delivery by runner form, whole-skip with a note (REV-03) | VERIFIED | `lens_delivery.py:73` `lens_set`, `:177` `check_lens`, `:199` `plan_lenses`, `:17` `LENS_NOTES` | `test_lens_delivery.py:43,91,130,181,263` (runner refusals, budget, order and UI, closed notes, prose bytes equal the runner), `test_compose_for_lane.py:224,261,283` |
| R6 | Skill-path setting per host, control set widened (REV-03, REV-04) | VERIFIED | runner `cross-ai.mjs:6678` control set equal to `prompt_guard.is_control_char` | `test_runner_skills_argv.py:91` pi path form, `:108` prose hosts keep argv, `tests/fixtures/prompt_control_chars.json` pinned both sides (`test_prompt_guard.py:289,302`) |
| R7 | Over-window prompt refused before spawn, never trimmed (REV-04) | VERIFIED | `prompt_guard.py:124,155,193` `estimate_tokens`, `window_for`, `check_window`; `REFUSED_EXIT = 65` `:32` | `test_prompt_guard.py:65` over refuses and equal passes, `:81` override beats catalog, `:92` unknown never capped, `:191` bracket form is unknown, `:227` two lanes independent; `test_compose_for_lane.py:61,169,183` no spawn on refusal |
| R8 | Control-char or out-of-root value rejected (REV-04) | VERIFIED | `prompt_guard.py:44,100` `is_control_char`, `validate_values`; roots `skill_table.py:464` | `test_prompt_guard.py:340` eight SPEC fixtures, `:371,395,408,454`; `test_compose_for_lane.py:192,309,337,412`; `test_capability_block.py:355` symlinked install |
| R9 | Opt-in after-approval edit pass (REV-03) | VERIFIED | `edit_pass.py` (`edit-lens-pass`, record, accept, reject) | `test_edit_pass.py:79` key unset runs nothing, `:95` read-only lane never chosen, `:119` rejected path skipped, `:157,176,269` accept, reject, byte-equal restore |
| R10 | GSD config skill reads the shared table (REV-05) | VERIFIED | `skill_scan.py` derives visibility; `inventory.py` `skill_roles`; `PONYTAIL_SKILLS` gone | `test_curated_config_skills.py:672` tuple absent (103 ran); byte-equal old output cases in the same module |
| R11 | One builder, three entry points, summary lines (REV-04, REV-05) | VERIFIED | `capability_block.py` `compose_for_lane`, `lane_summary`; `cli.py:1349,1375` | `test_capability_entry_points.py:132,135` byte-equal review and execute, `:53` `capability` key, `:138` config order, `:178` no lanes |
| R12 | Skill text, docs, closed lists, judge bar, guard (JDG-04) | VERIFIED | four SKILL.md files, `docs/config/design.md`, READMEs, template 11 to 12 (`cross_ai.py:60`) | `test_cross_ai_docs_text.py:223,233,238,243,253,259,274` (roles, refusal reasons, lens notes, sections, keys, capability fields); `test_arch_hardcoded_models` (23 ran) |

## Goal achievement: roadmap success criteria

| SC | Criterion | Status | Evidence |
|----|-----------|--------|----------|
| 1 | One table rescanned every run, jev sorter, owner confirms | VERIFIED | R1, R2 rows; scratch-HOME `skill-table` run in `ship-install.log:28-` shows a seeded-absent skill missing and a no-row skill `unsorted` |
| 2 | Capability block from the final argv, no shell no tool | VERIFIED | R3, R4. Own live runner dry run (below): pi review `shell: no`; `ship-install.log:226-246` pi review block has "none: this lane has no shell tool", no `rg`, no CLI line |
| 3 | Lens delivery by path or inlined, edit pass opt-in | VERIFIED by fixture | R5, R6, R9. pi gets `skill=lens-a applied form=path` in my live dry run; others get prose. Limit above (D-18 not run) |
| 4 | Over-window refused with reason, unknown not capped, bad embedded value rejected | VERIFIED | R7, R8; `ship-install.log:248-250` a path outside the roots gave `rc=65 path_outside_roots` |
| 5 | Changed SKILL.md meet the judge bar (JDG-04) | VERIFIED by grade, with open findings | See judge table |

## Judge loop 39 (R12 / JDG-04)

`python3 tools/judge_loop.py check .planning/judge` (I ran it, exit 0): every phase-39 skill reports `bar met: grade B or better`.

| Skill | Rounds | Worst percent / grade | Critical / high | Base | Regression |
|-------|--------|-----------------------|-----------------|------|-----------|
| ai-kit-spec-review | 3 | 82.4 B | 0 / 4 open | loop 36: 83.2 | none (-0.8) |
| ai-kit-spec-config | 3 | 84.0 B | 0 / 4 open | loop 37: 84.0 | none |
| ai-kit-cross-ai | 1 (fixed) | 84.8 B | 0 / 1 fixed | loop 38.1: 83.2 | none |
| ai-kit-gsd-curated-config | 1 (fixed) | 81.6 B | 0 / 3 fixed | loop 38: 85.6 | none |

The nine open findings are owner items (below). Every changed SKILL.md has a loop 39 record; the ROADMAP criterion cites JDG-04 and
`make check-dogfood` (its JDG-04 citation check) passed.

## Cross-checks

- **No feature removed:** `git diff --diff-filter=D --stat 04fd6ca..HEAD` printed nothing. Grok code is intact: `git diff 04fd6ca..HEAD -i -G grok -- skills tools tests docs README.md` is empty and `grok` counts in `detection.py` (6) and `cross-ai.mjs` (1) are equal at both commits.
- **Requirement IDs:** ROADMAP lists REV-03, REV-04, REV-05 (JDG-04 is the cross-cutting criterion 5). REQUIREMENTS.md lines 280, 289, 302 are `[x]` and the table rows 1110-1112 say Complete; each maps to the rows above (REV-03: R5, R6, R9; REV-04: R3, R4, R6, R7, R8, R11; REV-05: R1, R2, R10, R11). No orphan: the table maps no other id to Phase 39.
- **Edge coverage:** `edge_floor.py check 39-SPEC.md` (I ran it): `ok true`, 68 floor rows, 68 table rows, none missing.
- **ROADMAP and STATE:** the plans list shows 19/19 `[x]` and the dated 2026-11-23 notes exist (REQUIREMENTS 288, 301, 307; ROADMAP 977). STATE `stopped_at: Completed 39-19-PLAN.md` matches. The ROADMAP phase list line 129 is still `- [ ] Phase 39`, as expected before the orchestrator's phase completion; I did not change it.
- **Live runner copy:** `.planning/scripts/cross-ai.mjs` gave the same capability lines as the template in my dry run, and `check-dogfood` (pristine render) passed.

## What I ran myself (at 4544493)

| Check | Result |
|-------|--------|
| `tools/run_unittest_parallel.py` on 14 phase modules (skill_table, prompt_guard, lens_delivery, capability_block, capability_entry_points, compose_for_lane, edit_pass, runner_preview, runner_skills_argv, runner_flags, curated_config_skills, cross_ai_docs_text, config_role_write, config_status) | exit 0, 14/14 |
| same runner on test_ai_kit_spec (688), test_ai_kit_spec_superpowers (174), test_arch (118), test_arch_hardcoded_models, test_cross_ai_render_sync, test_runner_describe | exit 0, 6/6 |
| `edge_floor.py check 39-SPEC.md` | exit 0, ok true |
| `make check-dogfood` | exit 0, `check-dogfood: ok` (stale-digest notes only) |
| `tools/judge_loop.py check .planning/judge` | exit 0 |
| `tmp/verify-39/probe.py`: real node `--print-argv` per lane on template and live copy, scratch HOME | rc 0 for six lanes; pi review `write none, shell no`; pi exec all unknown; claude review all unknown; codex exec `write full, shell yes`; a control-character skill path gave rc 2 usage error; scratch dir removed |

Orchestrator gate logs of the final tip (`tmp/run-2026-11-19/gates-39b/`, written 17:11 to 17:24, after the 17:03 tip commit): `make test` exit 0 (185/185, 3/3, 9/9, 29/29, 2/2, installer 48 passed 0 failed), lint, validate, test-unit, e2e-test, e2e-test-modules, e2e-test-install, wizard-pty, e2e-docker (clean room PASS), edge-floor, check-dogfood and the installer dry run (`ship-install.log`, exit 0, scratch `.claude` empty after the dry run) all exit 0. The logs carry no commit sha, so "ran at 4544493" rests on their timestamps; my own runs above at 4544493 back it.

## Owner items and stated limits (not failures, not verified)

1. D-18 live probe and real-home probes not run, no consent line (see above). The mtime changes of `~/.claude/settings.json` and `~/.cursor/cli-config.json` seen during the phase have no known cause (39-19-SUMMARY); I did not touch real config.
2. The spec-review file-size finding (judge D5-1) needs a SPEC amendment: the SPEC pins the SKILL.md tables. 9 findings stay open after round 3 (spec-config 5, spec-review 4), bar met by grade.
3. The code review changed `ai-kit-spec-review/SKILL.md` by 10 lines after judge round 3 (commit 4544493: the profile cache root sentence). The skill's digest is stale by design (`check-dogfood` says so) and that text was not judged; it states what the code does.
4. A project's `.aikit/config.toml` `[skills.roles]` needs no trust step (owner decision); the other-worktree document reading and the skill-directory-as-root reading await owner confirmation (todo `2026-11-23-review-notes-left-open-by-phase-39`).
5. 11 deferred low review items and 39-17's digest/installer gap (todo and 39-17-SUMMARY).
6. The compose and dispatch paths are proven with a fake runner output and the real runner's dry run, not with a real host call. The edit pass runs only on codex lanes today (recorded decision). The tool-profile label of the codebase-memory-mcp seed stays unverified. The clean-room image has no node, so node-gated tests skip there only (by design, `require_real_node`).
7. Install on the real machine and the live re-check (ship step) are pending the owner.

## Gaps

None. No FAILED truth, no missing artifact, no unwired link, no debt marker found in the changed code by the review.

---

_Verified: 2026-11-23_
_Verifier: Claude (gsd-verifier)_
