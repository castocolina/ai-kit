---
phase: 6
reviewers: [opencode]
reviewed_at: 2026-09-11T01:26:04Z
cycles: 4
plans_reviewed: [06-01-PLAN.md, 06-02-PLAN.md, 06-03-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
cycle_2:
  reviewed_at: 2026-09-11T02:02:44Z
  reviewers: [opencode]
  models:
    opencode: "openai/gpt-5.6-sol (reasoning=high)"
  model_sources:
    opencode: "ladder-fallback: review.models.opencode pins xai/grok-4.6, which returned HTTP 403 personal-team-blocked:spending-limit (out of xAI credits) on invocation; .aikit/review-spec.toml's documented reviewer ladder (opencode-local-plan > opencode-sol > opencode-grok > codex-sol > native-opus) was applied manually and opencode-sol (openai/gpt-5.6-sol) succeeded with a full source-grounded review"
  lane_notes:
    - "opencode run emitted repeated 'permission requested: external_directory ... auto-rejecting' for /home/bazzite/.claude/*, /home/bazzite/.agents/*, /home/bazzite/.config/opencode/* during this cycle's run. Spot-checked citations into those paths (e.g. agent-md-refactor/SKILL.md, skill-judge/SKILL.md, naming-analyzer/SKILL.md) against the real files on disk and they are accurate, so the denials did not appear to block the grounding that mattered for this review."
cycle_3:
  reviewed_at: 2026-09-11T03:14:54Z
  reviewers: [opencode]
  models:
    opencode: "openai/gpt-5.6-sol (reasoning=high)"
  model_sources:
    opencode: "ladder-fallback: rung 1 (opencode-local-plan, router-env/my-plan-review) resolved to an unavailable backing model (claude/claude-opus-5) and errored immediately; rung 2 (opencode-sol, openai/gpt-5.6-sol) was invoked directly per .aikit/review-spec.toml's documented ladder and succeeded. xai/grok-4.6 (rung 3) was not attempted since rung 2 succeeded."
  lane_notes:
    - "First invocation attempt dispatched per-plan subagents via the ai-kit-spec-review-checklist + dispatching-parallel-agents skills; the 06-03 subagent failed on an 'external_directory' permission denial (/var/home/bazzite/.config/opencode/gsd-core/workflows/*, auto-rejecting), and the run ended with only a 3-line narrative status, not a structured review. Re-invoked with an explicit no-subagent instruction in the prompt; the second invocation completed a full structured per-plan review, reading all three plan files, REQUIREMENTS.md, ROADMAP.md, the source todo, Makefile, .pre-commit-config.yaml, and the installed agent-md-refactor/skill-judge/naming-analyzer SKILL.md files directly, with file:line citations throughout."
    - "One cited finding (06-03's rename/leftover scan matching untracked *.md files) cites this review run's own scratch prompt file (.tmp-gsd-review/prompt.md) as the triggering example; the underlying defect (the scan pattern is not restricted to tracked/renamed surfaces) is real and repo-general, not an artifact specific to that scratch file."
cycle_4:
  reviewed_at: 2026-09-11T03:49:00Z
  reviewers: [opencode]
  models:
    opencode: "openai/gpt-5.6-sol (reasoning=high)"
  model_sources:
    opencode: "ladder-fallback: rung 1 (opencode-local-plan, router-env/my-plan-review) resolved to an unavailable backing model (claude/claude-opus-5) and errored immediately; rung 2 (opencode-sol, openai/gpt-5.6-sol) was invoked directly per .aikit/review-spec.toml's documented ladder and succeeded on the first attempt with a full structured review, reading all three plan files, REQUIREMENTS.md, and ROADMAP.md directly with file:line citations throughout."
cycle_5:
  reviewed_at: 2026-09-11T05:00:22Z
  reviewers: [direct-verification]
  models:
    opencode: "unavailable (see lane_notes)"
  model_sources:
    opencode: "degraded: every rung of .aikit/review-spec.toml's ladder failed — rung 1 (opencode-local-plan) hung/timed out with no response; rung 2 (opencode-sol, openai/gpt-5.6-sol) returned 'usage limit reached' after succeeding on a trivial smoke-test seconds earlier, indicating the workspace's shared monthly spending cap was exhausted mid-run; rung 3 (opencode-grok, xai/grok-4.6) returned 'personal-team-blocked:spending-limit' (out of xAI credits); rung 4 (codex-sol) failed with an expired/already-used OAuth refresh token (HTTP 401). Five additional non-ladder opencode models (opencode-go/glm-5.3, opencode/nemotron-3.5-lightning-free, opencode/big-pickle x2, opencode/muse-spark-1.3-contributor-free) were also tried as a further fallback: one hit the same $10 workspace spending cap, one hung indefinitely, two terminated their turn after a one-line preamble with no review content (opencode CLI issue #1936), and one (muse-spark) produced output but explicitly declined to use its Read tool on the full file set, disclaiming that it reviewed only a truncated in-prompt excerpt with no fresh on-disk reads. None of the nine total invocation attempts produced a genuine source-grounded review. In place of the failed CLI lane, the orchestrating agent performed the fresh-file verification itself: read the current 06-01/06-02/06-03-PLAN.md content directly and checked it against every Cycle 4 HIGH/MEDIUM finding with file:line citations (see below)."
  lane_notes:
    - "This cycle's review is DEGRADED relative to cycles 1-4: no independent external-AI CLI completed a review. The findings below were produced by direct file-grounded reading rather than cross-AI dispatch, because every available opencode lane (and the codex fallback) was blocked by exhausted billing or expired auth in this environment."
---

# Cross-AI Plan Review — Phase 6

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## Cycle 1 (02ca473)

### OpenCode Review

I'll load the plan-review skills first, then verify each plan's claims against the repo.
Using the checklist reviewer against the GSD plans on disk. Grounding claims against the repo next.
Plans and wrapped skills exist. Next I’ll check Makefile, pre-commit, the 17-rule todo, AGENTS.md, and the cited skill patterns.
Grounded: `AGENTS.md:22` matches R01 signals; `agent-md-refactor` is process-only; usage-metrics tests use `sys.path.insert`, not `spec_from_file_location`.

#### 06-01

##### Summary
Plan 01 is a solid tracer for a stdlib checker package: structured `RULES`, live tool-presence (not assumed), hook-derived vs cache-sourced recommendations, and immediate gate registration. Two executable verifies will not do what the plan claims: the R01 live check contradicts this repo’s `AGENTS.md`, and the test loader copies the wrong precedent for a multi-module package.

##### Strengths
- Gate registration is copied from a real pattern: `Makefile:33-39`, `.pre-commit-config.yaml:21,48,53`, `pyproject.toml:87,93` already list `ai-kit-usage-metrics` the same way.
- `detect.py:47` really uses `shutil.which(..., path=search_path)` and does not touch `os.environ`; adapting that locally (no `tools/` import) matches Phase 3 layering.
- Entrypoint shape is real: `skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py:1-7` is shebang + `main(sys.argv[1:])`.
- D-04/D-06/D-07 are encoded as data and cache states (`absent`/`stale`/`fresh`), not prose. Hook-derived gaps correctly skip research.
- This repo’s `Makefile:33-45` lacks `setup-env`, `arch-test`, `test-unit`, and 1:1 hook targets, so the `arch-test` live verify against `.` is a true fixture.

##### Concerns
- **CRITICAL — Task 2 live verify cannot pass against this repo.** R01 signals include `"english only"` and `"non-negotiable"`. `AGENTS.md:22` is `English only, always`; `AGENTS.md:20` is `## Non-Negotiable Rules`. That is 2/3 signals → `present` → omitted from `workflow` (`include_present=False`). `assert 'R01' in ids` fails. The `<fails_when>` text even describes this as a “regression,” so the verify is self-contradictory.
- **HIGH — Wrong test-loader precedent.** Task 1 requires `importlib.util.spec_from_file_location` as in `tests/test_setup.py:15` / `tests/test_tool_substitution_hook.py:40-43` (single-file modules). This skill is a package with intra-package imports (`cli` → `makefile_checker` → `stack_cache`). The matching precedent is `tests/test_ai_kit_usage_metrics.py:16-21` (`sys.path.insert` of the skill dir, then `from ai_kit_usage_metrics.cli import main`). Literal `spec_from_file_location` of one file will not import the package.
- **HIGH — REQ-agtmd-makefile-rules is presence-only.** `REQUIRED_STATIC_TARGETS` checks names. This repo already has `validate:` at `Makefile:44-45` (`uv run pre-commit run --all-files`) and `test:` at `Makefile:33`. Those names would not be flagged, yet they do not chain per-hook targets lightest-first or alias `test-unit`. ROADMAP SC-1 and `REQUIREMENTS.md:56` include that chaining/alias structure. Plan 01 still claims the REQ is “fully implemented at the checker level.”
- **HIGH — Cache lookup key is internally inconsistent.** Findings use target `name` (`setup-env`); the example lookup is `tooling["setup_env"]`. No schema defines cache keys. Plan 02 cannot close D-04 without this.
- **MEDIUM — `main()` argv wiring for `check .` is not specified.** Verify runs `...py check .`; `usage-metrics` `main` (`cli.py:106-128`) takes only a subcommand, no path. Implementer must invent `argv[1]` → `repo_root`.
- **MEDIUM — TestGateRegistration is thinner than the precedent.** `tests/test_ai_kit_usage_metrics.py:3003-3026` asserts Makefile path, ruff *and* py-compile, unittest entry, and pyright include. Plan 01 omits ruff, Makefile `lint:` `py_compile` args, pyright, and vulture, and regex-tests a non-existent `skills/ai-kit-agents-md-checker/cli.py` instead of a nested package path.
- **MEDIUM — R17 criticality is required by Task 2 (`3`) but never assigned in Task 1.** Remaining rules’ `criticality`/`signals` are “read the todo,” except R01/R12/R02.

##### Suggestions
- Drop the live `R01 in ids` assert, or pin signals that this `AGENTS.md` does not match; keep the scratch-fixture unit test as the source of truth.
- Load tests like `test_ai_kit_usage_metrics.py:16-21`.
- Either parse `validate` recipes for hook-target chaining (and `test`/`test-unit` alias), or amend REQ/SC-1 to “target names present” and stop claiming the REQ is fully implemented.
- Freeze cache keys to Makefile target names (`setup-env`, `arch-test`, …) in `stack_cache.py` now.
- Copy the full `TestGateRegistration` surface from usage-metrics, using a nested path such as `skills/ai-kit-agents-md-checker/ai_kit_agents_md_checker/cli.py`.

##### Risk Assessment
**HIGH.** Architecture is right; the tracer’s own verifies and the Makefile-completeness claim will fail or silently under-implement SC-1.

#### 06-02

##### Summary
Plan 02 correctly splits `missing`/`near_miss`/`blocked`, adds `cache-update`, and documents D-05 inline-only reporting. It does not specify the cache JSON shape Plan 01 looks up, and it treats `/agent-md-refactor` as a per-rule insertion API that skill does not provide.

##### Strengths
- `auto_apply: status == "missing"` makes D-08 data, not comments; `blocked` vs `remediate` keeps research-blocked Makefile gaps out of `/agent-md-refactor`.
- `cache-update` reuses Plan 01 `write_stack_cache`; fail-closed invalid JSON (exit 1, no traceback) fits an agent-facing CLI.
- Wrap vs plain `/agent-md-refactor` is explicit (ROADMAP SC-3). D-05 is one unambiguous sentence.
- Threat T-06-06 is right: hand `/agent-md-refactor` only `rules.py` `summary`, never target-file text (`agent-md-refactor` `SKILL.md:1-34` is structural, no house rules).
- Entrypoint resolution can copy `skills/ai-kit-usage-metrics/SKILL.md:47-58` unchanged in shape.

##### Concerns
- **HIGH — D-04 loop cannot close with the documented research prompt.** Plan 01 looks up `tooling[target_name]`. Plan 02’s research prompt asks for formatter / scanner / smell / dead-code / test pyramid / validate order / pre-commit vs pre-push — category names, not `setup-env`/`arch-test`/`test-unit`. A fresh cache then still yields `recommendation: None` and `needs_research: True`. The must-have (“subsequent `check` reports `needs_research: False` with a real recommendation”) only holds if the test JSON uses invented keys the SKILL.md prompt never produces.
- **HIGH — `/agent-md-refactor` is not an insertion API.** `~/.claude/skills/agent-md-refactor/SKILL.md:27-34,39-59` is a 5-phase whole-file refactor; Phase 1 **asks the user to resolve contradictions before proceeding**. There is no CLI and no “insert this summary” mode. One invoke per rule, auto_apply without pause, fights that skill’s own confirmation gate and can run ~16 full refactors that prune each other’s inserts.
- **MEDIUM — D-01 “programmatic invoke.”** CONTEXT D-01 forbids “just documentation of a two-step workflow.” Plan 02 implements wrap as SKILL.md procedure. That is the only portable option (`agent-md-refactor` has no callable interface), but the plan never says so — an executor may try to import/subprocess a skill that is Markdown-only.
- **MEDIUM — `cache-update` vs default `CACHE_ROOT`.** Production write has no `--cache-root`; tests must monkeypatch. If the handler ignores `cache_root`, the test pollutes `~/.cache` or cannot assert `needs_research=False`.
- **MEDIUM — Multi-stack `blocked` entries.** `detect_stacks` can return several stacks (`stack_detect` markers). “The stack it needs research for” is unspecified when both `python` and `node` match.
- **LOW — Word-count vs required sections.** “Under 500 words” plus a full research prompt and wrap contract. This repo’s `ai-kit-usage-metrics/SKILL.md` is already 223 lines; skill-judge in 06-03 will be the real gate.

##### Suggestions
- Publish the cache JSON schema in Plan 02 Task 1: `tooling` keys **are** `REQUIRED_STATIC_TARGETS` names; put category research under those keys (e.g. `arch-test: pytest-archon`, `setup-env: ...`). Put that schema in the research-subagent prompt.
- Redefine wrap as: run `check`/`remediate`, then **one** `/agent-md-refactor` pass whose extra input is the ordered `remediate` list — or state that the wrapping agent inserts from `summary` and only uses `/agent-md-refactor` for structure, not 16× five-phase runs.
- State explicitly: no Python import of `agent-md-refactor`; SKILL.md *is* the program.
- Give `cache-update` an explicit `cache_root` argument (test-only, documented) rather than leaving monkeypatch as “your choice.”

##### Risk Assessment
**HIGH.** Payload/CLI shape is fine; D-04 and the wrap contract will not work as written against the real wrapped skill and the Plan 01 lookup.

#### 06-03

##### Summary
Plan 03 is the right close-out: skill-judge loop, naming-analyzer (not the provisional name), full rename of four gate surfaces, README row, grep for leftovers. It depends on 06-01/06-02 artifacts being correct and treats SC-3 distinctness as a SUMMARY note, not a test.

##### Strengths
- Rename blast radius is complete: directory, entrypoint, package, test module, `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`, SKILL.md `name:`.
- Second verify (`grep` old name outside `.planning/`) catches a dual-registration failure `make validate` could miss.
- README row format matches `README.md:26-38` (`| [\`name\`](skills/name/SKILL.md) | skill | one-line use case |`).
- skill-judge scores belong in SUMMARY, not a target-repo report file (correct reading of D-05).
- `naming-analyzer` and `skill-judge` are installed (`SKILLS_OK`).

##### Concerns
- **HIGH — Rename of a broken 06-01/06-02 surface.** If Plan 01’s loader/R01 verify or Plan 02’s cache schema is wrong, 06-03’s `make test && make lint && make validate` after rename only proves the name moved.
- **MEDIUM — skill-judge / naming-analyzer under `autonomous: true`.** Both are judgment skills, not CLIs. No fallback if invoke is skipped except “stop and surface.” Easy to checkbox-skip under autonomous execute.
- **MEDIUM — SC-3 evidence is a SUMMARY sentence.** “Run `check` on this repo and note that plain `/agent-md-refactor` does not run a house-rule check” is not automated. ROADMAP SC-3 is behavioral; a note is not a test.
- **MEDIUM — No skill-judge re-run after rename.** Frontmatter `name:` and every self-reference change; Task 1 already closed the loop.
- **LOW — README omits `ai-kit-usage-metrics` today** (`README.md:28-38`). Adding this skill is still correct; the table is already incomplete.
- **LOW — `files_modified` still lists the provisional path.** Fine as pre-rename; executor must not treat that list as the final tree.

##### Suggestions
- Make Task 2’s first step “re-run Plan 01/02 verifies under the provisional name; only then rename.”
- After rename, re-run skill-judge once, or state that a name-only change is exempt.
- Record the live `check` JSON (inline in SUMMARY) next to a one-line statement that `/agent-md-refactor` has no `check` subcommand — that is enough SC-3 evidence without a new file.

##### Risk Assessment
**MEDIUM** as its own plan (mechanical rename + review loop). **HIGH** as phase close-out, because it cannot repair 06-01/06-02 contract bugs.

---

##### Cross-plan
Cache key contract is undefined across 01→02. Wrap mechanism assumes an insertion API 02→03 never verifies. Task 2’s R01 live verify in 06-01 will fail before 06-02 starts if waves are sequential and autonomous.

##### Status: Issues Found — fix and re-invoke

---

### Cycle 1 Consensus Summary

Only one reviewer (OpenCode, `xai/grok-4.6`, reasoning=high) ran this cycle, so there is no cross-reviewer agreement/divergence to synthesize — all findings below are single-source. The reviewer explicitly grounded its findings against this repo (`AGENTS.md`, `Makefile`, test fixtures, the wrapped `agent-md-refactor` skill, and `ai-kit-usage-metrics` as precedent) and cited concrete `path:line` evidence throughout, so findings carry full source-grounded weight.

- CRITICAL: 06-01's Task 2 R01 live verify (`assert 'R01' in ids`) will fail against this repo's actual `AGENTS.md`, which already satisfies 2/3 R01 signals.
- HIGH: 06-01 copies the wrong test-loader precedent (`spec_from_file_location` vs `sys.path.insert` for a multi-file package).
- HIGH: 06-01's `REQUIRED_STATIC_TARGETS` check is presence-only and would pass this repo's `Makefile` despite missing the chaining/alias structure required by SC-1/REQUIREMENTS.md.
- HIGH: 06-01's cache lookup key (`name` vs `tooling["setup_env"]`) is internally inconsistent, blocking 06-02's D-04 closure.
- HIGH: 06-02's research prompt produces category-named answers that don't match the `REQUIRED_STATIC_TARGETS`-keyed cache lookup from 06-01.
- HIGH: 06-02 treats `/agent-md-refactor` as a per-rule insertion API, but that skill is a 5-phase whole-file refactor with a user-confirmation gate and no callable/insertion interface.
- HIGH: 06-03's rename/close-out cannot repair the underlying 06-01/06-02 contract bugs it depends on.

## Cycle 2

**Scope note:** `review.models.opencode` is pinned to `xai/grok-4.6`. That model returned `HTTP 403 personal-team-blocked:spending-limit` ("You have run out of credits or need a Grok subscription") on every invocation this cycle — a provider-side billing block, not a sandbox/repo-access failure. Per `.aikit/review-spec.toml`'s own documented fallback ladder (`opencode-local-plan` → `opencode-sol` → `opencode-grok` → `codex-sol` → `native-opus`), the next rung (`opencode-sol`, `openai/gpt-5.6-sol`) was invoked manually with the identical prompt/instructions this cycle built, and it completed with a full, source-grounded, all-plan-covered review. This is reported as a single real reviewer run (not a clean pass, not a blocked/degraded non-review) — the reviewer read and cited real repo files throughout, and spot-checks below confirm the citations.

**Grounding spot-check (by this orchestrator, not the reviewer):** two of the reviewer's `file:line` citations were independently re-read against the actual files — `/home/bazzite/.claude/skills/agent-md-refactor/SKILL.md:25-34` (Phase 1/contradiction-gate structure — confirmed verbatim) and the field sets in `06-01-PLAN.md:287-305` (Makefile findings: `target`/`present`/`recommendation`/`needs_research`/`stacks`, no `criticality`/`status`/`summary`) vs. `06-02-PLAN.md:37` (`build_remediation` claiming it reads `criticality`/`status`/`summary` off every finding) — both confirmed accurate. The reviewer's CRITICAL finding below is real, not a hallucinated citation.

### OpenCode Review (cycle 2, openai/gpt-5.6-sol fallback)

Using `ai-kit-spec-review-checklist` to audit the three GSD plans, `graphify` to ground codebase relationships, and `writing-clearly-and-concisely` to keep the report precise. Verified every Round 1 disposition against the on-disk plans and referenced source before assessing new risks. Round 1's loader and R01 fixes are present, but source tracing exposed fresh cross-plan contract risks around Makefile completeness and the remediation payload schema.

#### 06-01

##### Summary
The revision fixes the failed R01 assertion, package-loading precedent, cache-key spelling, CLI arguments, registration coverage, and explicit rule metadata. It remains incomplete against the Makefile and workflow requirements, and the revised cache logic introduces stale-cache and multi-stack correctness bugs.

##### Strengths
- The package-loading fix matches the real package precedent: `tests/test_ai_kit_usage_metrics.py:16-29` inserts the skill directory into `sys.path` before importing the package.
- The proposed live binary checks match `tools/hooks/detect.py:39-66`, which uses `shutil.which(..., path=search_path)`.
- Gate registration targets the correct existing surfaces: `Makefile:33-39`, `.pre-commit-config.yaml:14-21,44-53`, and `pyproject.toml:84-95`.
- The R01 live verification no longer assumes a specific missing rule, correctly accounting for `AGENTS.md:20-28`.
- The target-name cache schema is now consistent at `06-01-PLAN.md:237-268,287-304`.

##### Round 1 Dispositions
- **Resolved:** R01 live assertion, package loader, target-key spelling, CLI path argument, full registration test, explicit criticality/signals, and deterministic stack iteration.
- **Partially resolved:** The presence-only Makefile concern. Chain membership and aliasing were added, but other required forms of incompleteness remain.
- **Partially resolved:** Multi-stack handling is deterministic, but it still collapses a multi-stack repository to one recommendation.

##### Concerns
- **HIGH — Stale cache entries become trusted recommendations.** `get_stack_tooling()` returns tooling together with `needs_research=True` for stale data at `06-01-PLAN.md:255-268`, but `check_makefile_shape()` selects any non-`None` target entry and changes the result to `needs_research=False` at `06-01-PLAN.md:287-304`. This directly contradicts the stale-cache must-have at `06-01-PLAN.md:36,43`.
- **HIGH — Multi-stack repositories still collapse to one stack.** The checker takes the first sorted stack with a usable entry at `06-01-PLAN.md:296-303`. The source requirement calls for tooling accurate to detected "language(s)" at `.planning/todos/pending/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md:25-28`. If Python is cached and Node is stale, the checker reports success using Python alone and hides the missing Node research.
- **HIGH — REQ-agtmd-makefile-rules remains only partially implemented.** The requirement covers an "incomplete" structure and lightest-first ordering at `.planning/REQUIREMENTS.md:56`. The plan explicitly declines to verify ordering at `06-01-PLAN.md:330-335,619-625`, never inspects whether `setup-env` installs the required tool classes, and never checks other static-target recipes. Either the requirement must be formally narrowed or these checks must be implemented.
- **HIGH — Standard remote pre-commit hooks can disappear from the audit.** `parse_precommit_hooks()` only returns IDs paired with an inline `entry:` at `06-01-PLAN.md:281-290`. Many non-local pre-commit hooks declare an `id` without an inline entry. Such hooks would be absent from `hooks.keys()`, so the required 1:1 Makefile target check in `.planning/REQUIREMENTS.md:56` would silently miss them.
- **HIGH — Compound workflow rules can be falsely marked satisfied.** R04's signals contain no execution, cheap-model, or path-portability signal at `06-01-PLAN.md:208`; two review-only phrases satisfy the threshold at `06-01-PLAN.md:517-520`. That contradicts the independently mandatory review, execution, and path-agnostic clauses in `.planning/REQUIREMENTS.md:57`.
- **HIGH — Part of source rule R02 is never checked.** R02 has no prose signals and is excluded from workflow checking at `06-01-PLAN.md:193-206,511-512`. The required prohibition on skipping pre-commit except for red-to-green TDD appears in the source rule at `.planning/todos/pending/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md:36-38`.
- **HIGH — The seeded-cache tracer lacks a Python marker.** The scratch fixture is instructed to create only a Makefile and pre-commit file at `06-01-PLAN.md:393-404`, then seed the Python cache at `06-01-PLAN.md:405-411`. Since stack detection requires `pyproject.toml`, `requirements.txt`, `setup.py`, or `Pipfile` at `06-01-PLAN.md:231-235`, the cache cannot supply the asserted recommendation.
- **MEDIUM — The call-path contract disagrees with the implementation instructions.** The key link says `rule_checker.py` calls `tool_presence.check_tool_presence()` at `06-01-PLAN.md:55`; the action correctly places that call in `cli.py` at `06-01-PLAN.md:528-536`.

##### Suggestions
- Reject stale tooling before inspecting its entries, and add a stale-cache-through-checker regression test.
- Aggregate recommendations across every detected stack; retain `needs_research=True` until each applicable stack is covered.
- Parse all hook IDs and use `pre-commit run <id>` when no inline `entry:` exists.
- Add structural checks for `setup-env`, static test targets, and validation ordering, or formally amend `REQUIREMENTS.md` and `ROADMAP.md`.
- Give compound rules independently required signal groups rather than a single "half the phrases" threshold.
- Add a Python marker to the cache tracer fixture and test every complex rule's false-positive boundary.

##### Risk Assessment
**HIGH.** Several core requirements can silently pass while incomplete, and fresh versus stale recommendations are currently conflated.

#### 06-02

##### Summary
The one-pass `/agent-md-refactor` redesign is materially better and matches the real wrapped skill. However, Plan 02 consumes a remediation schema Plan 01 does not produce, cannot supply the near-miss evidence its confirmation flow requires, and accepts unvalidated cache data across an acknowledged trust boundary.

##### Strengths
- The single-invocation design matches the real five-phase whole-file process in `/home/bazzite/.claude/skills/agent-md-refactor/SKILL.md:25-34,39-86`.
- Near-miss confirmation is correctly separated from the wrapped skill's contradiction gate, whose actual purpose appears at `/home/bazzite/.claude/skills/agent-md-refactor/SKILL.md:39-59`.
- The exact hyphenated cache keys now agree with Plan 01 at `06-02-PLAN.md:25,181-197,305-312`.
- The explicit `--cache-root` option makes the write-path test isolated at `06-02-PLAN.md:163-180,186-197`.
- Inline-only reporting directly implements `06-CONTEXT.md:50-57`.

##### Round 1 Dispositions
- **Resolved:** Repeated per-rule refactors, cache-root ambiguity, word-count priority, and target-name key spelling.
- **Partially resolved:** "Programmatic invocation" remains only a prose instruction with no host-native skill-invocation contract.
- **Partially resolved:** Multi-stack blocked entries preserve all names only when no stack has usable data; Plan 01 hides partially covered stack sets.
- **Syntactically resolved but semantically incomplete:** The research JSON now round-trips, but the fixed seven-target schema cannot represent all dedicated formatter/security/dead-code recommendations demanded by the source rule.

##### Concerns
- **CRITICAL — The combined remediation interface is undefined.** Plan 02 claims Plan 01 attaches `criticality`, `status`, and `summary` to every consumed finding at `06-02-PLAN.md:37`. Plan 01's Makefile findings contain only `target`, `present`, `recommendation`, `needs_research`, and optional issue data at `06-01-PLAN.md:287-305,318-345`. Plan 02 nevertheless inserts them into the same ordered list at `06-02-PLAN.md:145-160`, while Step C consumes every entry's `summary` at `06-02-PLAN.md:276-283`. The Makefile entries cannot be ordered or handed off as specified. *(Confirmed by this orchestrator's own spot-check — see Cycle 2 scope note above.)*
- **HIGH — The near-miss confirmation flow requests evidence that no payload carries.** Step A requires the agent to name "current near-miss evidence" at `06-02-PLAN.md:262-265`. Plan 01 emits only ID, status, criticality, and summary at `06-01-PLAN.md:508-522`, and `build_remediation()` preserves only those fields at `06-02-PLAN.md:135-144`.
- **HIGH — `cache-update` accepts structurally invalid JSON.** It handles unreadable or syntactically invalid JSON at `06-02-PLAN.md:167-184`, but it never verifies that the result is an object keyed only by `REQUIRED_STATIC_TARGETS` with string recommendations. A valid JSON list or nested object can be cached and later break `.get()` or produce unusable recommendations. This crosses the explicitly recognized LLM-to-cache trust boundary at `06-02-PLAN.md:384-390`.
- **HIGH — The generated SKILL.md is explicitly host-specific.** It is instructed to use the Claude-style `Agent` tool and `subagent_type: general-purpose` at `06-02-PLAN.md:297-300`, and to link `~/.claude/skills/agent-md-refactor/SKILL.md` at `06-02-PLAN.md:331-333`. That conflicts with the requirement that skills work unmodified across conformant hosts at `AGENTS.md:79-82`.
- **HIGH — The cache schema cannot express the full tooling research result.** The research asks for formatter, security, smell, duplicate, dead-code, testing, ordering, and hook split at `06-02-PLAN.md:299-304`, but output is restricted to seven static target names at `06-02-PLAN.md:305-312`. It provides no structured way to recommend dedicated `format`, `security`, or `dead-code` targets when the project's current pre-commit config does not already contain them.
- **MEDIUM — D-01 remains only partially satisfied.** Context requires a "programmatic invoke, not just documentation of a two-step workflow" at `06-CONTEXT.md:22-29`. The revision names a precise handoff, but still describes natural-language execution and expressly adds no import or subprocess at `06-02-PLAN.md:283-292`. It should specify a host-native skill invocation with an explicit portable fallback contract.
- **MEDIUM — The behavior contract says the wrong return type.** `build_remediation()` is said to return a list at `06-02-PLAN.md:127-130`, while its implementation contract returns `{"remediate": [...], "blocked": [...]}` at `06-02-PLAN.md:160-161`.

##### Suggestions
- Define one remediation dataclass or exact dictionary schema shared by both plans, including `kind`, `id/target`, `criticality`, `summary`, `recommendation`, `evidence`, and `auto_apply`.
- Add matched signals or excerpts to near-miss findings and preserve them through remediation.
- Validate cache JSON before writing and reject unknown keys, non-string values, empty recommendations, and non-object roots.
- Replace Claude-specific tool names and install paths with host-neutral skill/subagent language; document unavoidable host gaps explicitly.
- Give stack research a richer internal schema, then derive Makefile-target recommendations from it.

##### Risk Assessment
**HIGH.** The wrapper's central payload cannot currently connect Plan 01 output to Plan 02's confirmation and single-invocation handoff.

#### 06-03

##### Summary
The close-out plan now includes post-rename skill review, README work, and stronger distinctness evidence. Several Round 1 fixes remain only narrative, and the unchanged-name branch is impossible under the unconditional rename and old-name grep.

##### Strengths
- The rename blast radius includes directory, entrypoint, package, test module, Makefile, pre-commit, type-check, dead-code, and README surfaces at `06-03-PLAN.md:226-261`.
- The existing registration locations named by the plan are accurate: `Makefile:33-39`, `.pre-commit-config.yaml:14-21,44-53`, and `pyproject.toml:84-95`.
- The README row format matches `README.md:24-38`.
- A post-rename `/skill-judge` pass is now explicit at `06-03-PLAN.md:263-268`.
- The installed `/agent-md-refactor` source does currently contain neither a checker nor house-rule data: `/home/bazzite/.claude/skills/agent-md-refactor/SKILL.md:25-34,39-86`.

##### Round 1 Dispositions
- **Resolved:** Post-rename skill-judge requirement, README gap note, and provisional-path annotation.
- **Partially resolved:** Pre-rename verification, non-skippable skill receipts, and automated distinctness evidence.
- **New defect:** Supporting "no rename needed" conflicts with unconditional movement and zero-old-name verification.

##### Concerns
- **HIGH — The unchanged-name branch cannot pass.** The analyzer may confirm the provisional name at `06-03-PLAN.md:220-224`, but the plan then unconditionally moves the directory onto `skills/<final>` at `06-03-PLAN.md:226-233` and requires zero occurrences of that still-valid name at `06-03-PLAN.md:288-290`. The analogous Phase 7 plan correctly makes movement and grep conditional at `.planning/phases/07-curated-gsd-config-skill/07-04-PLAN.md:231-248,281-282`.
- **HIGH — The claimed full pre-rename re-verification is not encoded as runnable checks.** The action claims every Plan 01/02 verify runs at `06-03-PLAN.md:141-153`, but the task's only pre-rename `<automated>` command is the unittest at `06-03-PLAN.md:171-173`. It omits Plan 01's live checks at `06-01-PLAN.md:448-455,550-564` and Plan 02's SKILL contract and full gates at `06-02-PLAN.md:336-355`.
- **HIGH — The skill-judge gate is weaker than Phase 6's authoritative criterion.** `REQUIREMENTS.md:58` and `ROADMAP.md:196` require no remaining Critical/Important finding. Plan 03 allows completion at 96/120 even with findings at `06-03-PLAN.md:155-165`. The installed judge defines a score and Critical Issues but no "Important" class at `/home/bazzite/.agents/skills/skill-judge/SKILL.md:528-582`, so the plan also lacks a severity mapping.
- **MEDIUM — Final-name conversion is ambiguous.** `<final>` is used as the complete directory name while the package becomes `ai_kit_<final_snake>` at `06-03-PLAN.md:226-240`. If `<final>` already includes `ai-kit-`, that formula can produce `ai_kit_ai_kit_*`; the actual precedent converts the complete `ai-kit-usage-metrics` name to `ai_kit_usage_metrics`, as shown by `tests/test_ai_kit_usage_metrics.py:16-29`.
- **MEDIUM — Naming-analyzer does not produce a mandatory single winner.** The installed skill analyzes files and directories and returns alternatives at `/home/bazzite/.agents/skills/naming-analyzer/SKILL.md:12-40,256-271`. Plan 03 does not define tie-breaking, prefix policy, or user confirmation when several names are recommended.
- **MEDIUM — Distinctness remains only partly automated.** The new checker's live command appears in prose at `06-03-PLAN.md:270-281`; the actual added `<verify>` checks only that `agent-md-refactor` lacks two literal strings at `06-03-PLAN.md:292-299`. That assertion does not prove the final checker command ran or returned non-empty findings.
- **MEDIUM — The rename audit is narrower than claimed.** The action promises a whole-tree search at `06-03-PLAN.md:245-249`, but the verify limits content to selected extensions and excludes ordinary Markdown such as `README.md` at `06-03-PLAN.md:288-290`. It also cannot detect stale filenames or the provisional cache namespace `ai-kit/agents-md-checker/stack-refs` established at `06-01-PLAN.md:251-255`.
- **LOW — README verification and attribution are weak.** No test asserts that the final README link exists. The plan calls this "AGENTS.md rule 11" at `06-03-PLAN.md:48,111`, but the current `AGENTS.md:20-52` contains no README-currency rule; that rule comes from the source todo at `.planning/todos/pending/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md:192-202`.

##### Suggestions
- Make movement and old-name checks conditional on whether the final name changed.
- Copy every prerequisite `<automated>` command literally into Task 1 or invoke a script that runs and records all of them.
- Require zero remaining blocking findings; define how skill-judge's actual report maps to "Important."
- Define `final_skill_name`, `final_suffix`, and `final_package_name` separately.
- Require a naming-analyzer receipt containing considered names, selected name, and selection reason.
- Add the renamed checker's live JSON assertion as an actual `<verify>`.
- Audit tracked filenames and all non-planning file contents, not selected extensions alone.

##### Risk Assessment
**HIGH.** The close-out can fail mechanically when the name remains unchanged and can declare success without executing all prerequisite or behavioral checks.

#### Cross-Plan Assessment
- Plan 01's Makefile findings do not satisfy Plan 02's remediation input contract.
- Plan 01 loses stale-state and partial multi-stack information before Plan 02 can dispatch research.
- The exact target-name cache fix resolves serialization but not the richer tooling requirement.
- Plan 03 cannot compensate for these defects because its prerequisite verification is incomplete and its final gate accepts a weaker condition than the roadmap.

**Overall risk: HIGH.** The plans should be revised before execution, primarily around one shared finding/remediation schema, all-stack cache freshness, complete Makefile semantics, and conditional final naming.

### Cycle 2 Consensus Summary

Only one reviewer ran this cycle (OpenCode, fallback model `openai/gpt-5.6-sol`, reasoning=high, substituted for the credit-blocked pinned `xai/grok-4.6` per the documented reviewer ladder — see the Cycle 2 scope note above). No cross-reviewer agreement/divergence to synthesize; all findings are single-source but source-grounded with `file:line` citations, spot-checked by this orchestrator.

Of Cycle 1's 7 HIGH-or-above findings, the planner's Round 1 ledgers (`06-01-PLAN.md`, `06-02-PLAN.md`, `06-03-PLAN.md` §"Review Dispositions Ledger") claimed all 7 addressed. This cycle's review confirms the literal Cycle 1 assertions (R01, loader, cache-key spelling) are genuinely fixed, but finds the fixes introduced or left in place a fresh, largely disjoint set of HIGH concerns:

- CRITICAL (new): 06-02's `build_remediation()` assumes every finding — including Plan 01's Makefile findings — carries `criticality`/`status`/`summary`, but Makefile findings carry only `target`/`present`/`recommendation`/`needs_research`/`stacks`. This breaks the Plan 01 → Plan 02 handoff for every Makefile-gap finding.
- HIGH (new): 06-01 stale cache entries are still treated as trusted recommendations (`needs_research` flips to `False` even when the underlying tooling entry was stale).
- HIGH (new): 06-01 multi-stack detection still collapses to the first stack with a usable entry rather than covering all detected stacks.
- HIGH (new): 06-01's Makefile/workflow-rule coverage has several specific remaining gaps — non-inline pre-commit hooks are invisible to the audit, compound rule R04's signal threshold can be satisfied without any execution/cheap-model/path-agnostic signal, and R02 is excluded from checking entirely.
- HIGH (new): 06-01's own scratch-fixture tracer cannot pass as written (no Python stack marker for the seeded Python cache).
- HIGH (new): 06-02's generated SKILL.md hardcodes Claude-specific tool names (`Agent` tool, `subagent_type: general-purpose`) and a `~/.claude/...` path, conflicting with this repo's own cross-host skill-portability rule.
- HIGH (new): 06-02's cache schema still cannot represent the full research categories (formatter/security/dead-code/etc.) it asks for — same shape of gap as Cycle 1's D-04 finding, not fully closed.
- HIGH (new): 06-03's "name unchanged" branch is logically impossible given the plan's own unconditional rename + zero-occurrence grep, and the claimed full pre-rename re-verification is not actually wired as runnable `<automated>` steps.
- HIGH (new): 06-03's skill-judge gate (96/120 pass threshold) is weaker than the phase's own "no remaining Critical/Important finding" success criterion, and the installed skill-judge has no "Important" severity class to map against.

REQUIREMENTS.md/ROADMAP.md wording — "REQ-agtmd-makefile-rules... a target per pre-commit hook 1:1... validate target chaining... lightest-first" — is cited directly by the reviewer as the source of several of the 06-01 gaps; these are requirement-level gaps the Cycle 1 fixes narrowed but did not close.

## Convergence Status (after Cycle 2)

Cycle 1's 7 HIGH-or-above concerns are resolved as literal assertions (per the ledgers, confirmed by Cycle 2's review). However, Cycle 2 finds the underlying cross-plan contract (Plan 01 finding schema ↔ Plan 02 remediation consumer) is still broken — in a new way (field-shape mismatch rather than key-spelling mismatch) — plus a fresh batch of HIGH-severity gaps in Makefile/workflow-rule completeness, cache freshness, multi-stack handling, host-portability, and the 06-03 rename/gate logic. None of these Cycle 2 findings appear in any plan's Review Dispositions Ledger yet (the ledgers only cover Cycle 1). This phase has not converged — another planning pass addressing Cycle 2's findings, followed by cycle 3 review, is needed before execution.

## Cycle 3

**Scope note:** `review.models.opencode` is pinned to `router-env/my-plan-review` (rung 1 of `.aikit/review-spec.toml`'s ladder), which resolved to a backing model (`claude/claude-opus-5`) reported as unavailable and errored immediately without running. Per the documented ladder (`opencode-local-plan` → `opencode-sol` → `opencode-grok` → `codex-sol` → `native-opus`), rung 2 (`opencode-sol`, `openai/gpt-5.6-sol`) was invoked directly and succeeded with a full source-grounded review. The first `opencode-sol` invocation attempted to dispatch per-plan subagents (via the `ai-kit-spec-review-checklist` + `dispatching-parallel-agents` skills); the 06-03 subagent failed on an external_directory permission denial and the run ended with only a 3-line narrative, not a structured review. A second invocation with an explicit no-subagent-dispatch instruction completed the full structured review below, reading all three plan files and cited repo files directly.

### OpenCode Review (cycle 3, openai/gpt-5.6-sol)

Using `ai-kit-spec-review-checklist` to verify the current GSD plans against Cycle 2 findings and identify revision-introduced concerns, auditing directly with no subagent dispatch. The Cycle 2 fixes materially repair the cache and finding-schema contracts, but the close-out plan still has executable verification gaps despite its revised prose.

#### 06-01

##### Summary
The revision resolves the Cycle 2 cache, multi-stack, finding-schema, fixture, and workflow-rule defects. However, the plan still does not fully implement the declared AGENTS.md/CLAUDE.md and Makefile requirements.

##### Strengths
- Stale entries are gated on both freshness and key presence in `_resolve_across_stacks()`, with a dedicated stale-cache test. Evidence: `06-01-PLAN.md:315-335,506-520`.
- Multi-stack resolution now requires fresh coverage for every detected stack and reports the uncovered stacks deterministically. Evidence: `06-01-PLAN.md:327-335,511-520`.
- Every Makefile finding now carries `criticality` and `summary`, matching the fields consumed by Plan 02. Evidence: `06-01-PLAN.md:424-430`.
- Non-inline pre-commit hooks remain visible through a `pre-commit run <id>` fallback. Evidence: `06-01-PLAN.md:302-313,341-348,491-499`.
- R04 now requires independent review, execution, and path-agnostic signal groups; R02 is included based on its non-empty signals. Evidence: `06-01-PLAN.md:210-215,630-659,681-689`.
- The tracer now creates a Python marker before exercising the Python cache. Evidence: `06-01-PLAN.md:478-505`.

##### Concerns
- **HIGH — The public CLI cannot check a CLAUDE.md-only repository.** `06-01-PLAN.md:432-449,665-673`; `.planning/REQUIREMENTS.md:55`. `main()` passes only `repo_root`, while `check()` defaults exclusively to `<repo>/AGENTS.md`; a repository containing only `CLAUDE.md` is treated as having an empty instruction file.
- **HIGH — The checker cannot see rules placed into linked files by the skill it wraps.** `06-01-PLAN.md:665-673`; `06-02-PLAN.md:317-347`; `agent-md-refactor/SKILL.md:76-82,110-145`. The wrapped skill deliberately moves testing, documentation, and git rules out of the root file, but the checker reads only the root AGENTS.md — a later run can falsely report those rules missing and reinsert duplicates. (Same root cause recurs in 06-02 as the wrapper inheriting this blind spot.)
- **HIGH — A missing Makefile or pre-commit config has no defined non-crashing behavior.** `06-01-PLAN.md:289-307,337-340`; `.planning/REQUIREMENTS.md:56`. The specified parsers directly read both paths with no absent-file handling, even though a missing Makefile is the strongest form of the gap the skill is supposed to report.
- **HIGH — Valid Make prerequisite chaining is ignored, and lightest-first ordering is explicitly omitted.** `06-01-PLAN.md:297-301,393-422,567-585,759-776`; `.planning/REQUIREMENTS.md:56`; `.planning/ROADMAP.md:191-196`. The plan examines recipes only and expressly declares cost ordering unimplemented while still claiming the requirement complete.
- **HIGH — No detected stack produces vacuous "fresh coverage."** `06-01-PLAN.md:315-356`. `missing` is empty, so `_resolve_across_stacks()` returns `("", False, [])`; the missing target then gets an empty recommendation and `needs_research: false`.
- **HIGH — The modern-CLI rule cannot enforce awareness of each installed tool.** `06-01-PLAN.md:216-219,617-628,630-663`; `.planning/REQUIREMENTS.md:57`. Presence is collapsed to one boolean and R06's signals mention only `rg`/`ripgrep`/generic "modern cli"; guidance can pass while omitting `bat`, `sd`, `fd`, and `eza`.
- **HIGH — Two newly added research categories can never be classified as covered.** `06-01-PLAN.md:360-385`. `validate-order` and `precommit-vs-prepush-split` keyword tuples are deliberately empty and empty categories are "NEVER skipped," so even a fully compliant repository receives perpetual findings.

##### Suggestions
- Add fixtures for a CLAUDE.md-only repo, linked progressive-disclosure files, no Makefile, no pre-commit file, prerequisite-based chaining, and no detected stack.
- Model modern CLI presence per executable rather than as one aggregate condition.
- Keep the documented heuristic limitations, but do not claim `REQ-agtmd-makefile-rules` complete while mandatory ordering remains unimplemented.

##### Risk Assessment
**HIGH.** Core Cycle 2 defects are repaired, but common repositories can still crash, be falsely classified, or fail supported-file requirements.

#### 06-02

##### Summary
The remediation contract now handles workflow and Makefile findings separately and consistently. The cache schema and host-portability changes are substantially improved, but the write boundary and blocked-research flow remain unsafe or ambiguous.

##### Strengths
- `build_remediation()` no longer reads workflow-only `status` fields from Makefile findings. Evidence: `06-02-PLAN.md:140-182`.
- Near-miss evidence is preserved through `matched_signals`. Evidence: `06-02-PLAN.md:153-162,215-223`.
- Cache JSON is validated for root type, allowed keys, and non-empty string values before writing. Evidence: `06-02-PLAN.md:189-205,224-233`.
- The generated skill is required to use host-neutral resolution, conditional examples, and a direct-in-context fallback rather than requiring Claude-specific dispatch. Evidence: `06-02-PLAN.md:260-265,329-360`.
- The combined cache schema now includes all requested target and research-category keys. Evidence: `06-02-PLAN.md:367-386`.

##### Concerns
- **HIGH — `cache-update` permits path traversal through the stack argument.** `06-01-PLAN.md:270-281`; `06-02-PLAN.md:184-205`. `cache_path()` joins `f"{stack}.json"` under the cache root, while the new CLI validates only the JSON payload. A path-like stack can escape the cache directory and atomically overwrite an unrelated JSON file.
- **HIGH — The blocked-research lifecycle has contradictory invocation semantics.** `06-02-PLAN.md:348-386`. The action says blocked work is deferred to a "LATER, separate invocation," then says remediation may be rerun in the "same or a later invocation."
- **MEDIUM — Cached research has no mandatory provenance contract.** `06-02-PLAN.md:361-386,461-475`; `.planning/PROJECT.md:23-29`. Freshness is timestamped, but a non-empty freeform string can still be unsourced or hallucinated.

##### Suggestions
- Validate the stack identifier before resolving any cache path.
- Make blocked research an explicit state machine with one tested continuation rule.
- Require citations or provenance within the cache value schema.

##### Risk Assessment
**HIGH.** The consumer-side Cycle 2 schema failure is fixed, but the newly exposed cache writer can escape its intended directory.

#### 06-03

##### Summary
The skill-judge gate is now aligned with the installed skill's actual report format, and the rename action has explicit changed/unchanged branches. The runnable verification does not fully implement those branches or the claimed re-verification coverage.

##### Strengths
- The plan accurately grounds `skill-judge` against its real `## Critical Issues` report section and no longer permits score-only passage. Evidence: `06-03-PLAN.md:135-155,180-195`; `skill-judge/SKILL.md:544-582`.
- Actual invocation of both `skill-judge` and `naming-analyzer` is mandatory, with a stop-on-unavailable policy. Evidence: `06-03-PLAN.md:128-133,256-263`.
- Rename actions are now conditionally described, and package prefixing avoids the specific double-prefix defect. Evidence: `06-03-PLAN.md:308-360`.
- Post-rename execution and distinctness checks dynamically discover the final skill path. Evidence: `06-03-PLAN.md:401-431`.

##### Concerns
- **HIGH — The claimed full pre-rename re-verification is still incomplete.** `06-03-PLAN.md:161-178,198-232`; `06-01-PLAN.md:558-565,695-710`; `06-02-PLAN.md:407-428`. Task 1 omits Plan 01's `arch-test` live assertion, and its copied Plan 02 SKILL.md assertion omits the host-neutral and portable-fallback assertions at `06-02-PLAN.md:419-420`.
- **HIGH — The no-rename branch remains incompatible with the runnable leftover check.** `06-03-PLAN.md:321-360,405-407`. The shell command is unconditional and returns failure when the provisional name correctly remains in live files; prose in `<fails_when>` cannot change the command's exit status.
- **HIGH — The expanded leftover scan is not worktree-safe.** `06-03-PLAN.md:348-353,405-407`. The revised `*.md` scan is not restricted to tracked/renamed surfaces, so it can fail on unrelated untracked markdown the plan must preserve (it also cannot detect stale filenames or the provisional cache namespace).
- **MEDIUM — Final-name normalization handles prefixes but not the complete identifier.** `06-03-PLAN.md:308-319`; `skill-judge/SKILL.md:220-223`. An analyzer result such as `agents_md_rules_checker` produces a frontmatter name containing underscores, which violates the installed skill-judge name rules.

##### Suggestions
- Copy the upstream verification commands byte-for-byte instead of maintaining reduced approximations.
- Use a branch-aware rename audit over tracked files.
- Normalize and validate the final identifier before any `git mv`.

##### Risk Assessment
**HIGH.** The prose design is improved, but the executable close-out can still fail in both rename branches and does not prove all upstream contracts.

#### Cycle 2 Disposition Table

| # | Cycle 2 finding | Verdict | Evidence |
|---|---|---|---|
| 1 | Makefile findings lacked the fields assumed by `build_remediation()` | **RESOLVED** | `06-01-PLAN.md:424-430` gives every Makefile finding `criticality` and `summary`; `06-02-PLAN.md:153-182` branches by finding kind. |
| 2 | Stale cache entries were trusted as recommendations | **RESOLVED** | `06-01-PLAN.md:315-335` requires `needs_research is False`; `:506-510` adds the stale-cache regression test. |
| 3 | Multi-stack detection collapsed to the first usable stack | **RESOLVED** | `06-01-PLAN.md:327-335,511-520` requires fresh coverage for every detected stack. |
| 4 | Non-inline hooks were invisible; R04 could pass without all clauses; R02 was excluded | **RESOLVED** | Non-inline fallback: `06-01-PLAN.md:302-313,341-348`; grouped R04: `:210-215,643-656`; R02 inclusion: `:213,633-659`. |
| 5 | The seeded Python-cache tracer had no Python stack marker | **RESOLVED** | `06-01-PLAN.md:478-505` writes `requirements.txt` before cache lookup. |
| 6 | Generated SKILL.md hardcoded Claude-only dispatch and path assumptions | **RESOLVED** | `06-02-PLAN.md:260-265,329-360` makes Claude dispatch an example only and defines a portable fallback. |
| 7 | Cache schema could not represent formatter/security/dead-code categories | **RESOLVED** | `06-01-PLAN.md:244-265,360-385` adds `RESEARCH_CATEGORIES`/`ALL_TOOLING_KEYS`; `06-02-PLAN.md:367-386` uses the combined schema. |
| 8 | The unchanged-name branch was impossible, and full pre-rename verification was not runnable | **PARTIALLY RESOLVED** | Action prose is conditional at `06-03-PLAN.md:321-360`, but the automated grep remains unconditional at `:405-407`; the Plan 01 arch-target check and two Plan 02 portability assertions remain omitted. |
| 9 | Skill-judge's score threshold was weaker than the phase criterion and "Important" was unmapped | **RESOLVED** | `06-03-PLAN.md:135-155,180-195` requires an empty `## Critical Issues` section. |

#### Cross-Document Consistency
- Plan 01 claims `REQ-agtmd-makefile-rules` complete while explicitly excluding lightest-first ordering, contradicting `.planning/REQUIREMENTS.md:56` and `.planning/ROADMAP.md:193`.
- Plans 01-02 describe support for AGENTS.md/CLAUDE.md-style files, but the only runnable CLI path defaults to AGENTS.md.
- Plan 03 claims every upstream verification is rerun, but its runnable commands are a reduced subset.
- The wrapper's root-only checker conflicts with `agent-md-refactor`'s documented linked-file output model.

##### Status: Issues Found — fix and re-invoke

---

### Cycle 3 Consensus Summary

Only one reviewer ran this cycle (OpenCode, fallback model `openai/gpt-5.6-sol`, reasoning=high — rung 1 of the ladder, `opencode-local-plan`, errored on an unavailable backing model before running). No cross-reviewer agreement/divergence to synthesize; all findings are single-source but source-grounded with `file:line` citations.

Of Cycle 2's 9 findings, 7 are confirmed RESOLVED and 1 (the 06-03 rename/verification finding) is PARTIALLY RESOLVED — the conditional rename prose was added but the automated leftover-grep and pre-rename re-verification steps remain unconditional/incomplete. The revisions also introduced or left in place 12 distinct HIGH-severity concerns across the three plans:

- HIGH: 06-01's public CLI cannot check a CLAUDE.md-only repository (defaults exclusively to `AGENTS.md`).
- HIGH: the checker (06-01) and its wrapper (06-02) cannot see rules `agent-md-refactor` moves into linked/progressive-disclosure files — a later run can falsely report those rules missing and reinsert duplicates.
- HIGH: 06-01 has no defined non-crashing behavior when the Makefile or pre-commit config is missing.
- HIGH: 06-01 ignores Make prerequisite chaining and explicitly omits lightest-first ordering while still claiming `REQ-agtmd-makefile-rules` complete.
- HIGH: 06-01's multi-stack resolver produces vacuous "fresh coverage" when no stack is detected at all.
- HIGH: 06-01's modern-CLI rule collapses per-tool presence (`rg`/`bat`/`sd`/`fd`/`eza`) into one boolean, so guidance can pass while omitting four installed tools.
- HIGH: 06-01 adds two new research categories (`validate-order`, `precommit-vs-prepush-split`) with empty keyword sets, so they can never be classified as covered — perpetual false positives.
- HIGH: 06-02's `cache-update` CLI permits path traversal through an unvalidated `stack` argument, allowing an atomic overwrite of an arbitrary JSON file under the cache root.
- HIGH: 06-02's blocked-research lifecycle gives contradictory invocation semantics (deferred to a "later, separate invocation" vs. "same or later invocation").
- HIGH: 06-03's claimed full pre-rename re-verification omits Plan 01's `arch-test` live assertion and two Plan 02 SKILL.md portability assertions.
- HIGH: 06-03's no-rename branch is still incompatible with its own unconditional leftover-grep, which fails even when the provisional name correctly remains.
- HIGH: 06-03's expanded leftover/rename scan is not restricted to tracked or renamed surfaces, so it can fail on unrelated untracked markdown.

Two actionable non-HIGH concerns are not yet incorporated or explicitly deferred: 06-02's cached research has no mandatory provenance/citation contract (MEDIUM), and 06-03's final-name normalization does not cover the complete identifier, so an analyzer result with underscores can violate skill-judge's own naming rules (MEDIUM).

## Convergence Status (after Cycle 3)

Cycle 2's 9 findings are 7/9 RESOLVED and 1/9 PARTIALLY RESOLVED (that same finding, the Makefile-completeness claim, is also re-raised in Cycle 3 as a distinct HIGH about chaining/lightest-first ordering). Cycle 3 finds 12 distinct HIGH-severity concerns remaining across the three plans — seven in 06-01 (CLAUDE.md-only support, linked-file blind spot, missing-config crash behavior, chaining/ordering, empty-stack vacuous success, per-tool modern-CLI coverage, unsatisfiable research categories; the linked-file blind spot is shared with 06-02 and counted once), two more in 06-02 (cache-update path traversal, contradictory blocked-research semantics), and three in 06-03 (incomplete pre-rename re-verification, no-rename-branch/leftover-grep incompatibility, non-worktree-safe rename scan) — plus 2 actionable MEDIUM concerns (cache provenance, final-name normalization) not yet incorporated or deferred. This phase has not converged. Another planning pass addressing Cycle 3's findings, followed by cycle 4 review, is needed before execution.

## Cycle 4

**Scope note:** Rung 1 (`opencode-local-plan`, `router-env/my-plan-review`) errored immediately on an unavailable backing model (`claude/claude-opus-5`), as in cycles 2-3. Rung 2 (`opencode-sol`, `openai/gpt-5.6-sol`) was invoked directly and succeeded on the first attempt — no subagent-dispatch retry was needed this cycle. The reviewer read `06-01/02/03-PLAN.md`, `06-CONTEXT.md`, `REQUIREMENTS.md`, and `ROADMAP.md` directly and verified each Cycle 3 finding against the current (post-fix, commits `72323d6`/`bfe43c7`/`0b4e69b`) file content, with file:line citations throughout.

### OpenCode Review (cycle 4, openai/gpt-5.6-sol)

#### Cycle 3 Disposition Table

| # | Cycle 3 finding | Verdict | Evidence |
|---|---|---|---|
| 1 | CLI can't check a CLAUDE.md-only repo | **RESOLVED** | CLI falls back from `AGENTS.md` to `CLAUDE.md`, with dedicated coverage (`06-01-PLAN.md:840-870,908-914`). |
| 2 | Checker can't see rules moved into linked/progressive-disclosure files | **RESOLVED** | Classification includes one-hop, same-repo Markdown links matching the refactor skill's structure (`06-01-PLAN.md:840-870,915-922`). |
| 3 | No non-crashing behavior for missing Makefile/pre-commit config | **RESOLVED** | Missing files return empty parser results and maximal target findings rather than crashing (`06-01-PLAN.md:317-327,395-407,922-927`). |
| 4 | Prerequisite chaining ignored, lightest-first omitted, REQ still claimed complete | **PARTIALLY RESOLVED** | Prerequisite chaining now supported, but lightest-first ordering remains unverified despite being mandatory, while the plan still claims ROADMAP SC-1 satisfied (`06-01-PLAN.md:504-535,1026-1054`; `REQUIREMENTS.md:56`). |
| 5 | Multi-stack resolver vacuous "fresh coverage" with zero detected stacks | **RESOLVED** | Zero detected stacks now explicitly produce `needs_research: True`, with regression coverage (`06-01-PLAN.md:363-376,934-939`). |
| 6 | Modern-CLI rule collapses per-tool presence into one boolean | **RESOLVED** | R06 now records per-tool presence and requires separate signals for every installed modern CLI tool (`06-01-PLAN.md:759-780,805-826`). |
| 7 | Two research categories with empty keyword sets, perpetual false positives | **PARTIALLY RESOLVED** | The implementation section removes both empty-keyword categories, but a must-have elsewhere still says `RESEARCH_CATEGORIES` contains them — an internal contradiction (`06-01-PLAN.md:41,46,251-276`). |
| 8 | `cache-update` path-traversal via unvalidated `stack` argument | **RESOLVED** | Stack identifiers validated before path construction; CLI catches `ValueError` without writing (`06-01-PLAN.md:289-302`; `06-02-PLAN.md:210-223`). |
| 9 | Blocked-research lifecycle contradictory invocation semantics | **PARTIALLY RESOLVED** | Same-or-later-invocation research is now allowed, but inline research after Steps A-C can repeat Steps A-C and invoke `agent-md-refactor` twice, violating the exactly-once contract (`06-02-PLAN.md:321-326,387-400`). |
| 10 | Pre-rename re-verification omits arch-test + two portability assertions | **RESOLVED** | All five prerequisite verification commands wired, including the arch-test and both portability assertions (`06-03-PLAN.md:162-192,212-254`). |
| 11 | No-rename branch incompatible with unconditional leftover-grep | **RESOLVED** | No-rename branch now exits successfully before the leftover grep runs (`06-03-PLAN.md:399-408,453-455`). |
| 12 | Leftover scan not restricted to tracked/renamed surfaces | **RESOLVED** | Leftover scan now uses `git grep` over tracked files only, excluding `.planning` artifacts (`06-03-PLAN.md:387-397,453-455`). |
| a | Cached research has no mandatory provenance contract (MEDIUM) | **PARTIALLY RESOLVED** | Provenance is required, but validation accepts any string containing `"(source:"`, including an empty/malformed citation (`06-02-PLAN.md:197-207,247-260`). |
| b | Final-name normalization handles prefixes but not the complete identifier (MEDIUM) | **RESOLVED** | Normalization now lowercases and replaces underscores/repeated hyphens across the complete identifier, not only its prefix (`06-03-PLAN.md:331-358`). |

#### New Findings (introduced by or surviving the Cycle 3 revision)

- **HIGH** — A valid prerequisite alias such as `test: test-unit` is falsely reported as `not_aliased` because alias detection checks only recipe substrings or identical recipes; prerequisite aliasing must itself be recognized and tested (`06-01-PLAN.md:536-546`).
- **HIGH** — The pre-commit/pre-push split check passes when any hook has a push stage, without establishing that slow hooks were actually moved there, while the requested research can't be consumed through `ALL_TOOLING_KEYS` (`06-01-PLAN.md:483-496`; `06-02-PLAN.md:410-435`).
- **HIGH** — Pre-commit hook-id parsing only matches literal `- id: <name>` lines, silently omitting valid quoted YAML ids from the mandatory 1:1 target audit (`06-01-PLAN.md:350-361`).
- **HIGH** — Validate-chain recipe matching uses raw substrings, so a target named `lint` can appear wired merely because the recipe contains `pylint` — matching must be token/command-aware (`06-01-PLAN.md:512-526`).
- **HIGH** — The rename verifier treats ANY surviving provisional directory as an intentional no-rename outcome, so a skipped/incomplete rename can bypass the leftover audit entirely; it must compare against the analyzer's recorded final name, not just directory existence (`06-03-PLAN.md:399-408,453-455`).
- **MEDIUM** — Complete-name normalization neither rejects nor normalizes unsupported characters, empty suffixes, or leading/trailing hyphens before constructing the final skill/package identifiers (`06-03-PLAN.md:331-358`).
- **MEDIUM** — Linked-file containment lacks a symlink-safe realpath contract, allowing a lexically in-repository link to resolve outside the repository (`06-01-PLAN.md:854-860,994-1007`).
- **MEDIUM** — Negating `git grep`'s exit status conflates "no matches" (exit 1) with a real grep error (exit >1) into the same success path; these must be distinguished (`06-03-PLAN.md:453-455`).

##### Status: Issues Found — fix and re-invoke

### Cycle 4 Consensus Summary

Only one reviewer ran this cycle (OpenCode, fallback model `openai/gpt-5.6-sol`, reasoning=high — rung 1 errored on an unavailable backing model before running, as in cycles 2-3). No cross-reviewer agreement/divergence to synthesize; all findings are single-source but source-grounded with file:line citations, and the reviewer verified every Cycle 3 finding against the current post-fix file content rather than trusting commit messages.

Of Cycle 3's 12 HIGH findings, 8 are confirmed RESOLVED and 4 are PARTIALLY RESOLVED (lightest-first ordering still unverified despite the claim of completeness; an internal contradiction left the removed research categories still named in a must-have; the exactly-once `agent-md-refactor` invocation contract can still be violated by repeated inline research; cache provenance validation accepts empty/malformed citations). Of the 2 Cycle 3 MEDIUM findings, 1 is RESOLVED and 1 is PARTIALLY RESOLVED (provenance format is checked but not content).

The revision also surfaced 5 NEW HIGH findings (prerequisite-alias false negative, pre-commit/pre-push split research not consumable, quoted-YAML hook-id parsing gap, substring-only validate-chain matching, rename verifier trusting directory existence over the analyzer's recorded name) plus 3 NEW MEDIUM findings (identifier normalization gaps, non-symlink-safe link containment, `git grep` exit-status conflation).

CYCLE_SUMMARY: current_high=8 current_actionable=4

## Convergence Status (after Cycle 4)

This phase has NOT converged after 4 cycles. The pattern across cycles 2→3→4 is a near-constant HIGH count (9→12→8, counting partial-resolutions as still-open) rather than a shrinking one — each round of fixes resolves most prior findings but surfaces a comparable number of new ones in the same checker-logic area (Makefile/prerequisite parsing, rename/leftover verification, cache provenance). This suggests the remaining defects are concentrated in a few genuinely hard sub-problems (Make recipe/prerequisite semantics, git-tracked-file leftover scanning, exactly-once research invocation) rather than superficial oversights, and another full replan-and-review cycle is likely to follow the same pattern without a more targeted fix strategy for those specific sub-problems.

## Cycle 5

**Scope note / DEGRADED REVIEW:** Every rung of `.aikit/review-spec.toml`'s documented ladder
failed this cycle — rung 1 (`opencode-local-plan`) hung/timed out with no response; rung 2
(`opencode-sol`, `openai/gpt-5.6-sol`, the model that produced cycles 2-4's reviews) returned
"usage limit reached" despite succeeding on a trivial smoke-test seconds before the real
invocation, indicating the workspace's shared spending cap was exhausted mid-run; rung 3
(`opencode-grok`, `xai/grok-4.6`) returned `personal-team-blocked:spending-limit` (out of xAI
credits); rung 4 (`codex-sol`, via the `codex` CLI) failed with an expired/already-used OAuth
refresh token (HTTP 401). Five further non-ladder opencode models were also tried as a fallback
(`opencode-go/glm-5.3` — hit the same spending cap; `opencode/nemotron-3.5-lightning-free` — hung
indefinitely; `opencode/big-pickle` — twice terminated its turn after a one-line preamble with no
review content; `opencode/muse-spark-1.3-contributor-free` — produced text but explicitly declined
to use its Read tool on the full file set, disclaiming it reviewed only a truncated in-prompt
excerpt with no fresh on-disk reads). Nine total invocation attempts, zero produced a genuine
source-grounded review. No external-AI CLI review ran this cycle.

**In place of the failed CLI lane**, the orchestrating agent performed the fresh-file
verification the cycle required directly: read the current `06-01-PLAN.md`, `06-02-PLAN.md`, and
`06-03-PLAN.md` content (not commit messages) and checked it against every one of Cycle 4's 8 HIGH
and 4 actionable MEDIUM findings, with file:line citations. This is a single-source, non-adversarial
verification pass, not a cross-AI review — it confirms whether the fix commits' claims match the
text on disk, but it is not an independent AI's fresh read of the plans for novel defects the way
cycles 2-4 were.

#### Cycle 4 Disposition Table

| # | Cycle 4 finding | Severity | Verdict | Evidence |
|---|---|---|---|---|
| 1 | Prerequisite alias (`test: test-unit`) falsely reported `not_aliased` | HIGH | **RESOLVED** | `_recipe_mentions_target` word-boundary helper plus explicit Make-prerequisite-listing check now satisfies alias detection (`06-01-PLAN.md:536-608`). |
| 2 | Pre-commit/pre-push split satisfied by ANY hook having a push stage; research not consumable via `ALL_TOOLING_KEYS` | HIGH | **RESOLVED** | `check_precommit_prepush_split` now checks each classified-slow hook's OWN YAML block for its own `stages:` value; Plan 02's research prompt no longer names an uncontained topic (`06-01-PLAN.md:483-526`; `06-02-PLAN.md:451,477,682`). |
| 3 | Pre-commit hook-id parsing matched only literal unquoted `- id:` lines, omitting quoted YAML ids | HIGH | **RESOLVED** | Parser now matches bare, double-, and single-quoted id tokens, keyed by the bare unquoted string (`06-01-PLAN.md:177-178,350-361,676-680`). |
| 4 | Validate-chain/alias matching used raw substrings (`lint` matched inside `pylint`) | HIGH | **RESOLVED** | Shared `_recipe_mentions_target` helper uses `\b{name}\b` word-boundary regex, never substring, for both chain-membership and alias checks (`06-01-PLAN.md:531-546`). |
| 5 | Rename verifier treated ANY surviving provisional directory as an intentional no-rename outcome | HIGH | **RESOLVED** | Check now reads a durable recorded-decision breadcrumb (`./tmp/agents-md-checker-final-name.txt`) written before any rename attempt and fails when the provisional directory survives but the recorded decision names a different final name (`06-03-PLAN.md:51`). |
| 6 | Lightest-first cost-ordering unverified despite SC-1 claimed satisfied | HIGH (carried, partial) | **RESOLVED** | Plan's own success criteria/`<done>` now explicitly state cost-ORDER is not mechanically verified, only chain/alias MEMBERSHIP, and no longer claim SC-1 unqualifiedly satisfied (`06-01-PLAN.md:47,1164-1167`). |
| 7 | `RESEARCH_CATEGORIES` must-have still named `validate-order`/`precommit-vs-prepush-split`, contradicting the implementation removing them | HIGH (carried, partial) | **RESOLVED** | Must-have text now explicitly lists the five real categories and explicitly excludes both removed categories, citing the prior contradiction (`06-01-PLAN.md:46`). |
| 8 | Exactly-once `/agent-md-refactor` invocation contract violable by repeated inline research after Steps A-C | HIGH (carried, partial) | **RESOLVED** | Step D, when chosen, now always completes and refreshes the list BEFORE Steps A-C begin; explicit rule rules out a second A-C pass in the same invocation (`06-02-PLAN.md:34,404-429,493-494`). |
| a | Cached research provenance validation accepted any string containing bare `"(source:"`, including empty/malformed citations | MEDIUM (carried, partial) | **RESOLVED** | Validation now also rejects a citation that is present but empty or whitespace-only (`06-02-PLAN.md:29,141,208-216,266-273`). |
| b | Identifier normalization neither rejected nor normalized unsupported characters, empty suffixes, or leading/trailing hyphens | MEDIUM | **RESOLVED** | Normalization now runs over the complete identifier, normalizes unsupported characters to `-` before collapse/trim, and stops the task on an empty result (`06-03-PLAN.md:48,334-364`). |
| c | Linked-file containment had no symlink-safe realpath contract | MEDIUM | **RESOLVED** | Containment now computed via `os.path.realpath` on both the repo root and the candidate link target, rejecting any path that escapes via a symlink (`06-01-PLAN.md:50,955-967`). |
| d | Negating `git grep`'s exit status conflated "no matches" with a real grep error | MEDIUM | **RESOLVED** | Check now distinguishes exit `1` (no matches, success) from any other non-zero exit (real error, explicit failure) (`06-03-PLAN.md:51`). |

#### New Findings (introduced by or surviving this fix round)

- **MEDIUM** — `check_validate_order` emits a SECOND, separate finding (`{"category": "validate-order", "issue": "validate_order_unverified"}`) whenever `chain_incomplete` was already raised, restating the same underlying gap with its own `needs_research: False` and a concrete `recommendation` (`06-01-PLAN.md:480-489`). Plan 02's `build_remediation()` has no merge/dedup rule for this pairing — it reads `recommendation`/`needs_research` off every finding uniformly (`06-02-PLAN.md:135-138`) — so a single Makefile gap (an unwired chainable target) now surfaces as TWO separate `auto_apply=True` entries in the `remediate` list with overlapping recommendations, rather than one. This is newly introduced by this fix round's own solution to Cycle 3's vacuous-category problem, not a Cycle 4 carryover. No test in either plan's `<verify>` section checks for this duplication (`06-01-PLAN.md:1065`, `06-02-PLAN.md` test list).

##### Status: Issues Found — fix and re-invoke

### Cycle 5 Consensus Summary

No external-AI CLI reviewer ran this cycle (see DEGRADED REVIEW scope note above) — every rung of
the documented ladder plus five additional opencode models all failed on exhausted billing, expired
auth, or unreliable early termination. The findings below come from the orchestrating agent's own
direct, file-grounded read of the current plan text, not an independent AI's review.

All 8 of Cycle 4's HIGH findings (5 new + 3 carried-over partial-resolutions) and all 4 of its
actionable MEDIUM findings are confirmed RESOLVED against the current `06-01/02/03-PLAN.md` text,
each with a concrete mechanism (word-boundary regex, per-hook push-stage check, quoted-YAML id
parsing, recorded-decision breadcrumb, realpath containment, exit-status distinction, non-empty
citation validation, full-identifier normalization) rather than a prose-only restatement of the
finding.

One NEW MEDIUM finding was identified: Cycle 3's fix for the vacuous `validate-order` research
category (converting it to a dedicated structural check) causes a single chain-incomplete gap to
now emit two separate, overlapping remediation entries with no dedup rule joining them.

CYCLE_SUMMARY: current_high=0 current_actionable=1

## Convergence Status (after Cycle 5)

This phase has NOT formally converged — no external-AI CLI completed an adversarial review this
cycle due to an exhausted review environment (billing caps on every paid opencode/codex lane, and
free-tier opencode models too unreliable to complete a review of this plan size). Pending that
caveat, direct verification found all of Cycle 4's HIGH and actionable MEDIUM findings resolved in
the current plan text, with one newly-introduced MEDIUM (duplicate remediation entries for a single
validate-chain gap). Recommend: (1) fix the new MEDIUM by having `check_validate_order` either skip
emitting `validate_order_unverified` when `chain_incomplete` already covers the same gap, or have
`build_remediation()` dedup findings that share a `recommendation`/root cause; (2) re-run this cycle
with an actual cross-AI CLI once the opencode workspace's spending cap resets or an alternative
reviewer (gemini, qwen, a topped-up codex session) is available, since a single self-verification
pass is not a substitute for the adversarial review this loop is designed to get.
