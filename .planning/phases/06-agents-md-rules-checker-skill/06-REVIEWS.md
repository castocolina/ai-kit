---
phase: 6
reviewers: [opencode]
reviewed_at: 2026-09-11T01:26:04Z
plans_reviewed: [06-01-PLAN.md, 06-02-PLAN.md, 06-03-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 6

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll load the plan-review skills first, then verify each plan's claims against the repo.
Using the checklist reviewer against the GSD plans on disk. Grounding claims against the repo next.
Plans and wrapped skills exist. Next I’ll check Makefile, pre-commit, the 17-rule todo, AGENTS.md, and the cited skill patterns.
Grounded: `AGENTS.md:22` matches R01 signals; `agent-md-refactor` is process-only; usage-metrics tests use `sys.path.insert`, not `spec_from_file_location`.

## 06-01

### Summary
Plan 01 is a solid tracer for a stdlib checker package: structured `RULES`, live tool-presence (not assumed), hook-derived vs cache-sourced recommendations, and immediate gate registration. Two executable verifies will not do what the plan claims: the R01 live check contradicts this repo’s `AGENTS.md`, and the test loader copies the wrong precedent for a multi-module package.

### Strengths
- Gate registration is copied from a real pattern: `Makefile:33-39`, `.pre-commit-config.yaml:21,48,53`, `pyproject.toml:87,93` already list `ai-kit-usage-metrics` the same way.
- `detect.py:47` really uses `shutil.which(..., path=search_path)` and does not touch `os.environ`; adapting that locally (no `tools/` import) matches Phase 3 layering.
- Entrypoint shape is real: `skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py:1-7` is shebang + `main(sys.argv[1:])`.
- D-04/D-06/D-07 are encoded as data and cache states (`absent`/`stale`/`fresh`), not prose. Hook-derived gaps correctly skip research.
- This repo’s `Makefile:33-45` lacks `setup-env`, `arch-test`, `test-unit`, and 1:1 hook targets, so the `arch-test` live verify against `.` is a true fixture.

### Concerns
- **CRITICAL — Task 2 live verify cannot pass against this repo.** R01 signals include `"english only"` and `"non-negotiable"`. `AGENTS.md:22` is `English only, always`; `AGENTS.md:20` is `## Non-Negotiable Rules`. That is 2/3 signals → `present` → omitted from `workflow` (`include_present=False`). `assert 'R01' in ids` fails. The `<fails_when>` text even describes this as a “regression,” so the verify is self-contradictory.
- **HIGH — Wrong test-loader precedent.** Task 1 requires `importlib.util.spec_from_file_location` as in `tests/test_setup.py:15` / `tests/test_tool_substitution_hook.py:40-43` (single-file modules). This skill is a package with intra-package imports (`cli` → `makefile_checker` → `stack_cache`). The matching precedent is `tests/test_ai_kit_usage_metrics.py:16-21` (`sys.path.insert` of the skill dir, then `from ai_kit_usage_metrics.cli import main`). Literal `spec_from_file_location` of one file will not import the package.
- **HIGH — REQ-agtmd-makefile-rules is presence-only.** `REQUIRED_STATIC_TARGETS` checks names. This repo already has `validate:` at `Makefile:44-45` (`uv run pre-commit run --all-files`) and `test:` at `Makefile:33`. Those names would not be flagged, yet they do not chain per-hook targets lightest-first or alias `test-unit`. ROADMAP SC-1 and `REQUIREMENTS.md:56` include that chaining/alias structure. Plan 01 still claims the REQ is “fully implemented at the checker level.”
- **HIGH — Cache lookup key is internally inconsistent.** Findings use target `name` (`setup-env`); the example lookup is `tooling["setup_env"]`. No schema defines cache keys. Plan 02 cannot close D-04 without this.
- **MEDIUM — `main()` argv wiring for `check .` is not specified.** Verify runs `...py check .`; `usage-metrics` `main` (`cli.py:106-128`) takes only a subcommand, no path. Implementer must invent `argv[1]` → `repo_root`.
- **MEDIUM — TestGateRegistration is thinner than the precedent.** `tests/test_ai_kit_usage_metrics.py:3003-3026` asserts Makefile path, ruff *and* py-compile, unittest entry, and pyright include. Plan 01 omits ruff, Makefile `lint:` `py_compile` args, pyright, and vulture, and regex-tests a non-existent `skills/ai-kit-agents-md-checker/cli.py` instead of a nested package path.
- **MEDIUM — R17 criticality is required by Task 2 (`3`) but never assigned in Task 1.** Remaining rules’ `criticality`/`signals` are “read the todo,” except R01/R12/R02.

### Suggestions
- Drop the live `R01 in ids` assert, or pin signals that this `AGENTS.md` does not match; keep the scratch-fixture unit test as the source of truth.
- Load tests like `test_ai_kit_usage_metrics.py:16-21`.
- Either parse `validate` recipes for hook-target chaining (and `test`/`test-unit` alias), or amend REQ/SC-1 to “target names present” and stop claiming the REQ is fully implemented.
- Freeze cache keys to Makefile target names (`setup-env`, `arch-test`, …) in `stack_cache.py` now.
- Copy the full `TestGateRegistration` surface from usage-metrics, using a nested path such as `skills/ai-kit-agents-md-checker/ai_kit_agents_md_checker/cli.py`.

### Risk Assessment
**HIGH.** Architecture is right; the tracer’s own verifies and the Makefile-completeness claim will fail or silently under-implement SC-1.

## 06-02

### Summary
Plan 02 correctly splits `missing`/`near_miss`/`blocked`, adds `cache-update`, and documents D-05 inline-only reporting. It does not specify the cache JSON shape Plan 01 looks up, and it treats `/agent-md-refactor` as a per-rule insertion API that skill does not provide.

### Strengths
- `auto_apply: status == "missing"` makes D-08 data, not comments; `blocked` vs `remediate` keeps research-blocked Makefile gaps out of `/agent-md-refactor`.
- `cache-update` reuses Plan 01 `write_stack_cache`; fail-closed invalid JSON (exit 1, no traceback) fits an agent-facing CLI.
- Wrap vs plain `/agent-md-refactor` is explicit (ROADMAP SC-3). D-05 is one unambiguous sentence.
- Threat T-06-06 is right: hand `/agent-md-refactor` only `rules.py` `summary`, never target-file text (`agent-md-refactor` `SKILL.md:1-34` is structural, no house rules).
- Entrypoint resolution can copy `skills/ai-kit-usage-metrics/SKILL.md:47-58` unchanged in shape.

### Concerns
- **HIGH — D-04 loop cannot close with the documented research prompt.** Plan 01 looks up `tooling[target_name]`. Plan 02’s research prompt asks for formatter / scanner / smell / dead-code / test pyramid / validate order / pre-commit vs pre-push — category names, not `setup-env`/`arch-test`/`test-unit`. A fresh cache then still yields `recommendation: None` and `needs_research: True`. The must-have (“subsequent `check` reports `needs_research: False` with a real recommendation”) only holds if the test JSON uses invented keys the SKILL.md prompt never produces.
- **HIGH — `/agent-md-refactor` is not an insertion API.** `~/.claude/skills/agent-md-refactor/SKILL.md:27-34,39-59` is a 5-phase whole-file refactor; Phase 1 **asks the user to resolve contradictions before proceeding**. There is no CLI and no “insert this summary” mode. One invoke per rule, auto_apply without pause, fights that skill’s own confirmation gate and can run ~16 full refactors that prune each other’s inserts.
- **MEDIUM — D-01 “programmatic invoke.”** CONTEXT D-01 forbids “just documentation of a two-step workflow.” Plan 02 implements wrap as SKILL.md procedure. That is the only portable option (`agent-md-refactor` has no callable interface), but the plan never says so — an executor may try to import/subprocess a skill that is Markdown-only.
- **MEDIUM — `cache-update` vs default `CACHE_ROOT`.** Production write has no `--cache-root`; tests must monkeypatch. If the handler ignores `cache_root`, the test pollutes `~/.cache` or cannot assert `needs_research=False`.
- **MEDIUM — Multi-stack `blocked` entries.** `detect_stacks` can return several stacks (`stack_detect` markers). “The stack it needs research for” is unspecified when both `python` and `node` match.
- **LOW — Word-count vs required sections.** “Under 500 words” plus a full research prompt and wrap contract. This repo’s `ai-kit-usage-metrics/SKILL.md` is already 223 lines; skill-judge in 06-03 will be the real gate.

### Suggestions
- Publish the cache JSON schema in Plan 02 Task 1: `tooling` keys **are** `REQUIRED_STATIC_TARGETS` names; put category research under those keys (e.g. `arch-test: pytest-archon`, `setup-env: ...`). Put that schema in the research-subagent prompt.
- Redefine wrap as: run `check`/`remediate`, then **one** `/agent-md-refactor` pass whose extra input is the ordered `remediate` list — or state that the wrapping agent inserts from `summary` and only uses `/agent-md-refactor` for structure, not 16× five-phase runs.
- State explicitly: no Python import of `agent-md-refactor`; SKILL.md *is* the program.
- Give `cache-update` an explicit `cache_root` argument (test-only, documented) rather than leaving monkeypatch as “your choice.”

### Risk Assessment
**HIGH.** Payload/CLI shape is fine; D-04 and the wrap contract will not work as written against the real wrapped skill and the Plan 01 lookup.

## 06-03

### Summary
Plan 03 is the right close-out: skill-judge loop, naming-analyzer (not the provisional name), full rename of four gate surfaces, README row, grep for leftovers. It depends on 06-01/06-02 artifacts being correct and treats SC-3 distinctness as a SUMMARY note, not a test.

### Strengths
- Rename blast radius is complete: directory, entrypoint, package, test module, `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`, SKILL.md `name:`.
- Second verify (`grep` old name outside `.planning/`) catches a dual-registration failure `make validate` could miss.
- README row format matches `README.md:26-38` (`| [\`name\`](skills/name/SKILL.md) | skill | one-line use case |`).
- skill-judge scores belong in SUMMARY, not a target-repo report file (correct reading of D-05).
- `naming-analyzer` and `skill-judge` are installed (`SKILLS_OK`).

### Concerns
- **HIGH — Rename of a broken 06-01/06-02 surface.** If Plan 01’s loader/R01 verify or Plan 02’s cache schema is wrong, 06-03’s `make test && make lint && make validate` after rename only proves the name moved.
- **MEDIUM — skill-judge / naming-analyzer under `autonomous: true`.** Both are judgment skills, not CLIs. No fallback if invoke is skipped except “stop and surface.” Easy to checkbox-skip under autonomous execute.
- **MEDIUM — SC-3 evidence is a SUMMARY sentence.** “Run `check` on this repo and note that plain `/agent-md-refactor` does not run a house-rule check” is not automated. ROADMAP SC-3 is behavioral; a note is not a test.
- **MEDIUM — No skill-judge re-run after rename.** Frontmatter `name:` and every self-reference change; Task 1 already closed the loop.
- **LOW — README omits `ai-kit-usage-metrics` today** (`README.md:28-38`). Adding this skill is still correct; the table is already incomplete.
- **LOW — `files_modified` still lists the provisional path.** Fine as pre-rename; executor must not treat that list as the final tree.

### Suggestions
- Make Task 2’s first step “re-run Plan 01/02 verifies under the provisional name; only then rename.”
- After rename, re-run skill-judge once, or state that a name-only change is exempt.
- Record the live `check` JSON (inline in SUMMARY) next to a one-line statement that `/agent-md-refactor` has no `check` subcommand — that is enough SC-3 evidence without a new file.

### Risk Assessment
**MEDIUM** as its own plan (mechanical rename + review loop). **HIGH** as phase close-out, because it cannot repair 06-01/06-02 contract bugs.

---

### Cross-plan
Cache key contract is undefined across 01→02. Wrap mechanism assumes an insertion API 02→03 never verifies. Task 2’s R01 live verify in 06-01 will fail before 06-02 starts if waves are sequential and autonomous.

### Status: Issues Found — fix and re-invoke

---

## Consensus Summary

Only one reviewer (OpenCode, `xai/grok-4.6`, reasoning=high) ran this cycle, so there is no cross-reviewer agreement/divergence to synthesize — all findings below are single-source. The reviewer explicitly grounded its findings against this repo (`AGENTS.md`, `Makefile`, test fixtures, the wrapped `agent-md-refactor` skill, and `ai-kit-usage-metrics` as precedent) and cited concrete `path:line` evidence throughout, so findings carry full source-grounded weight.

### Agreed Strengths
N/A — single reviewer this cycle.

### Agreed Concerns
N/A — single reviewer this cycle. Highest-severity single-source findings:
- CRITICAL: 06-01's Task 2 R01 live verify (`assert 'R01' in ids`) will fail against this repo's actual `AGENTS.md`, which already satisfies 2/3 R01 signals.
- HIGH: 06-01 copies the wrong test-loader precedent (`spec_from_file_location` vs `sys.path.insert` for a multi-file package).
- HIGH: 06-01's `REQUIRED_STATIC_TARGETS` check is presence-only and would pass this repo's `Makefile` despite missing the chaining/alias structure required by SC-1/REQUIREMENTS.md.
- HIGH: 06-01's cache lookup key (`name` vs `tooling["setup_env"]`) is internally inconsistent, blocking 06-02's D-04 closure.
- HIGH: 06-02's research prompt produces category-named answers that don't match the `REQUIRED_STATIC_TARGETS`-keyed cache lookup from 06-01.
- HIGH: 06-02 treats `/agent-md-refactor` as a per-rule insertion API, but that skill is a 5-phase whole-file refactor with a user-confirmation gate and no callable/insertion interface.
- HIGH: 06-03's rename/close-out cannot repair the underlying 06-01/06-02 contract bugs it depends on.

### Divergent Views
N/A — single reviewer this cycle.
