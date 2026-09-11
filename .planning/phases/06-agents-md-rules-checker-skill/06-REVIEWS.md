---
phase: 6
reviewers: [opencode]
reviewed_at: 2026-09-11T01:26:04Z
cycles: 2
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
