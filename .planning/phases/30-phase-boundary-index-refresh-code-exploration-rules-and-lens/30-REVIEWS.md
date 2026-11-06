---
phase: 30
cycle: 1
reviewers: [referee-one, referee-two, referee-three]
reviewed_at: 2026-11-05T10:11:39-03:00
plans_reviewed: [30-01-PLAN.md, 30-02-PLAN.md, 30-03-PLAN.md, 30-04-PLAN.md, 30-05-PLAN.md, 30-06-PLAN.md, 30-07-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
  referee-two: "router-env/my-referee-two"
  referee-three: "router-env/my-referee-three"
model_sources:
  referee-one: "pinned"
  referee-two: "pinned"
  referee-three: "pinned"
---

# Cross-AI Plan Review — Phase 30

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## Review conditions

Cycle 1 (the only cycle for this phase, owner priority speed), over the seven plans at `1bc229d`. Each configured
reviewer was probed once with a one-word prompt (09:47). The prompts were split into three batches (A 30-01, 30-02
and 30-03, wave 1; B 30-04 and 30-05; C 30-06 and 30-07), each inlining PROJECT.md (first 80 lines), the ROADMAP
Phase 30 section, the FLOW-04, -06, -12, -13, DESIGN-01, LENS-01 and JDG-04 lines, 30-SPEC.md, 30-CONTEXT.md, the
batch's plans, the source-grounding instructions, the ponytail lens and the batch's plan coverage manifest. Each
batch ran through the opencode lane (`review-lane invoke --slug opencode --as <instance>`), at most two at a time,
each call in its own process group, with a 15-minute no-output-growth stall watch.

- **referee-one** (`router-env/my-referee-one`): probe OK in 9 s. Every batch produced full per-plan sections with
  `file:line` evidence: A (30-01, 30-02, 30-03) 983 s, B (30-04, 30-05) 581 s, C (30-06, 30-07) 674 s. No retry,
  stall or quota stop.
- **referee-two** (`router-env/my-referee-two`): **failed** at the probe after 89 s (exit 1):
  `Error: Model grok-cli/grok-4.7-xhigh is unavailable`. Not dispatched; no substitute.
- **referee-three** (`router-env/my-referee-three`): **failed** at the probe after 88 s (exit 1):
  `Error: Model anthropic/claude-opus-5-5-xhigh is unavailable`. Not dispatched; no substitute.

Only one reviewer produced a review, so the consensus gate does not apply: every finding counts once the
orchestrator confirms it against the plan text, the installed GSD workflows and the source.

## OpenCode Review (referee-one)

### Batch A (30-01, 30-02, 30-03)

Using `ai-kit-spec-review-checklist` and the ponytail lens to check all three plans against source. I’ll keep this read-only and won’t run tests.

##### Document Type
GSD · implementation plans. All three plans were read from disk and checked against referenced source. Related plans were consulted only for dependencies and handoffs.

#### 30-01

##### Summary
The index engine has a sensible shared entrypoint, explicit degraded behavior, and unusually detailed acceptance cases. However, its concurrency design is incomplete: GSD can write the graph during this engine’s build, foreground lock holders can strand queued worktrees, and existing test callers can discard the proposed fake-tool PATH. These issues affect the phase’s central guarantees—not just implementation polish.

##### Strengths
- **Reuses the existing flow infrastructure appropriately.** `common_dir()` already provides an absolute, repository-wide location, and `render()` supplies the planned report format (`skills/ai-kit-commit-fold/scripts/flow_record.py:101-104`, `:220-223`). There is no need for another repository-identity or reporting abstraction.
- **The detached launch specifies the important pipe and lock details.** Inheriting the acquired lock fd and redirecting all standard streams avoids a launch-time lock gap and inherited-output-pipe blocking (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:233`).
- **Real GSD status is a valuable integration check.** The planned assertion checks `built_at_commit`, not merely the engine’s status file (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:185-191`). That matches GSD’s actual implementation, which reads the build commit from `graph.json` (`.claude/gsd-core/bin/lib/graphify.cjs:464-474`, `:500-503`).

##### Concerns
- **HIGH — GSD locking happens after the conflicting operation.**  
  The plan waits on `.rebuild.lock` only **before copying**, after running `graphify update .` (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:198`). GSD’s rebuilder holds that lock while running its own update against the same `graphify-out/` files (`.claude/hooks/lib/gsd-graphify-rebuild.sh:23-35`). The two builds can therefore overlap before the planned wait. Checking an absent PID file also does not reserve it against GSD’s independent check (`.claude/hooks/gsd-graphify-update.sh:128-136`). The PID-only fixture does not exercise shared-output contention.

- **HIGH — Worktree jobs can remain queued indefinitely behind a foreground refresh.**  
  `detach()` enqueues but launches no runner when the index lock is held; bare `index` acquires that same lock without a queue-draining obligation (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:233-234`). The dependent boundary implementation likewise refreshes only its current checkout (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:126`). If either foreground command owns the lock when a worktree is added, no drainer necessarily remains afterward. The e2e’s explicit `--drain` can conceal this production failure.

- **HIGH — Adding fakes to `git_env()` does not protect all existing callers.**  
  The plan assumes prepending the fake directory there isolates every flow test (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:160`). Existing callers replace the returned PATH with `host_fakes.host_path(bin_dir)` (`tests/test_flow_contract.py:64-72`; `tests/test_ai_kit_commit_fold_e2e.py:400-402`). That helper defaults to the process PATH, discarding the fixture PATH (`tests/host_fakes.py:68-70`). Once `start` invokes refresh, these paths can reach real indexers.

- **HIGH — An old graph can be advertised as a successful fresh build.**  
  Output validation requires only an existing, nonempty JSON object (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:161`), after which the engine writes successful status for HEAD (`:198`). A zero-exit/no-output run can leave a previous graph intact; `{}` also satisfies the described object check. GSD derives commit freshness from the graph itself and does not include commits-behind in its `stale` boolean (`.claude/gsd-core/bin/lib/graphify.cjs:464-498`). The missing case is: build at A, advance to B, then return success without producing B’s graph.

- **MEDIUM — [ponytail] The exclude-file recipe can target the caller’s repository.**  
  The plan opens the output of `git -C top rev-parse --git-path info/exclude` without specifying how relative output is resolved (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:196`). An output such as `.git/info/exclude` is relative to the target checkout, not necessarily Python’s cwd. Reuse `flow_record.common_dir(top) / "info" / "exclude"`—the exact pattern already used by `_ensure_ignored()` (`skills/ai-kit-commit-fold/scripts/flow_record.py:199-207`).

- **MEDIUM — Detached e2e processes lack failure-path cleanup.**  
  The test specifies a successful drain but no registered, bounded cleanup for timing assertion failures or later job-producing additions (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-01-PLAN.md:226`, `:236`). Its detached runners start new sessions, outside the test module’s process group. The runner’s cleanup operates on the registered module group, so it cannot guarantee those descendants are stopped (`tools/run_unittest_parallel.py:462-479`, `:498-510`).

##### Suggestions
- Specify coordination with GSD **before building**, including the acquisition race and failure-status writes. Do not claim mutual exclusion from an observation-only PID check.
- Make every index-lock holder drain or hand off pending work before finishing. Test this without manually invoking `--drain`.
- Audit existing PATH replacements and preserve `env["PATH"]` through `host_path(bin_dir, env["PATH"])`.
- Validate a usable graph and its build commit before recording success; add stale-output and empty-object cases.
- Register fixture-owned process cleanup before spawning any detached work, and place the final completion barrier after all additions.

##### Risk Assessment
**HIGH.** The normal path is well specified, but locking and queue ownership currently permit overlapping builds and missed indexing. Test isolation also needs correction before attaching refresh to existing flow commands.

#### 30-02

##### Summary
This plan is mostly focused and proportionate: a shared rule text, existing house-rule summaries, a runbook, and contract tests are all required deliverables. The main gap is that it treats ai-kit’s local instruction sentence as the general superpowers pre-plan integration. There are also smaller applicability and documentation inaccuracies that exact-text tests would preserve rather than detect.

##### Strengths
- **Preserving R07/R08 identity and signal vocabulary avoids unnecessary checker churn.** The current entries use distinct tool-presence conditions and stable signals (`skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:135-156`); the plan explicitly retains them while changing summaries (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:96-121`).
- **The design rule faithfully preserves the owner’s scope decision.** The proposed bullet explicitly makes ponytail govern implementation rather than feature completeness, including the MVP and no-jev cases (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:150`). This matches the locked design requirement (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-SPEC.md:229-239`).
- **The freshness distinction is source-grounded.** The proposed runbook separates age/build-status staleness from commits-behind (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:147`), matching `.claude/gsd-core/bin/lib/graphify.cjs:461-504`.

##### Concerns
- **HIGH — The superpowers pre-plan guarantee is not established by the proposed handoff.**  
  The new rule tells a session to run bare `fold.py boundary --next --point plan` and brief the plan writer (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:115-116`). However, the adapter explicitly starts after superpowers has already written and committed the plan (`skills/ai-kit-spec-execute-superpowers/references/start-step.md:6-10`). The dependent plan confirms it relies on this instruction-file fallback, still flagged for owner confirmation (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md:61`, `:70-80`). A target project need not contain ai-kit’s AGENTS.md, and the bare command has no script-resolution instructions. This does not yet satisfy the general before-planning requirement.

- **MEDIUM — [ponytail] R07 remains inactive for the newly important CLI-only case.**  
  The plan changes only the summary and preserves the condition (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:98`, `:119`). Actual codegraph presence is currently defined solely as a `.codegraph/` directory (`skills/_shared/ai_kit_rules_common/tool_presence.py:35`). Thus a project with the CLI installed but no index—the exact target of automatic initialization—does not activate R07. Reuse and extend `check_tool_presence()` rather than adding another detector; its graphify branch already demonstrates CLI-or-directory detection (`:36-39`).

- **MEDIUM — The graph-location wording omits existing configuration behavior.**  
  The canonical clauses and runbook describe `.planning/graphs/` as where GSD agents read the graph without qualification (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:111-112`, `:145-148`). GSD actually honors `graphify.graph_path` and uses that directory only as the default (`.claude/gsd-core/bin/lib/graphify.cjs:378-399`). Its build command also stops unless `graphify.enabled` is explicitly true (`.claude/commands/gsd-graphify.md:32-40`). Keep the locked two-location instructions, but label the default location and enabled-only copy condition accurately.

- **MEDIUM — The generated-block test specifies opposite comparisons.**  
  The plan requires the design rule above generated content (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md:45`), but its test action says the bullet’s offset is “below” the marker while simultaneously requiring marker-before-bullet to fail (`:152`). The locked requirement is unambiguous: above the generated block (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-SPEC.md:409`).

##### Suggestions
- Resolve the flagged owner decision before publishing the pre-plan guarantee. Provide a portable, reachable pre-plan route and reuse the existing fold resolver (`skills/ai-kit-spec-execute-superpowers/references/start-step.md:20-32`).
- Add an end-to-end checker case for “codegraph installed, no local index,” not just summary-equality assertions.
- Pin the graph-location and enabled-state qualifications in the documentation tests.
- Define the ordering predicate explicitly as `bullet_offset < marker_offset`, with fixtures for both orders.

##### Risk Assessment
**MEDIUM overall, with one HIGH integration blocker.** Most changes are straightforward and justified. The pre-plan fallback needs resolution; otherwise the documentation would promise broader delivery than the implementation provides.

#### 30-03

##### Summary
The byte-oriented, marker-scoped edit is the right approach for this sensitive change, and backup-first, dry-run, idempotency, and scratch-HOME coverage are strong foundations. The plan nevertheless misses important existing wizard paths and does not bind confirmation to the exact reviewed files. Backup-name collisions and the config-doctor result contract also need explicit treatment before this becomes the writer of global instructions.

##### Strengths
- **The pure bytes transform fits the preservation requirement.** Restricting replacement to the marker’s inner span and testing CRLF, non-ASCII text, and an outside-block duplicate directly tests the required behavior (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:93-106`), rather than relying on a text rewrite that could normalize unrelated bytes.
- **The write recipe follows established durability mechanics.** Sibling temporary files, fsync, preserved modes, and atomic replacement match existing writers (`tools/config_doctor_appliers.py:109-142`; `tools/setup.py:1878-1919`).
- **The doctor row correctly avoids runtime-config-file gating.** `runtime="cross"` and `reads_section_file=False` let the instruction-file check run independently of settings JSON (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:136`). This matches how cross rows are evaluated (`tools/config_doctor_checks.py:1067-1071`).

##### Concerns
- **HIGH — [ponytail] Wizard state is placed in a host-specific model, and housekeeping can remove the new item.**  
  The plan stores previews in `WizardModel.meta` and tests a manually populated model (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:159`, `:166-168`). In production, that metadata is host-specific: `_host_pane()` takes `host.segment_meta`, while the zero-host pane receives `{}` (`tools/wizard_app.py:320-324`, `:330-354`). More importantly, housekeeping rebuilds the selection from components and hooks only (`tools/setup.py:3849-3873`), then replaces the live selection (`tools/wizard_app.py:1056-1061`). The plan does not update this second builder, so users with pending housekeeping can lose the global-rules item entirely. Use component-level context for this component-level feature and cover the real builders.

- **HIGH — Confirmation is not bound to the files whose diffs were reviewed.**  
  Review captures `plan_changes(env)`, but confirmation calls `apply(rules_env, dry)` with only the environment (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:106`, `:159-166`). That call can discover a newly drifted file or a changed symlink target and rewrite it even though its diff was never shown. The post-backup reread protects only the fresh apply-time snapshot, not the reviewed snapshot. The repository already handles this distinction for status-line adoption: it refuses when the approved wiring value changed (`tools/setup.py:3729-3741`).

- **HIGH — Backup filenames can overwrite an earlier backup.**  
  The prescribed name contains only host, second-resolution timestamp, and basename, and is published through atomic replacement (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:106`). Two attempts within one second can reuse the same destination, losing the earlier recovery copy. Existing `_backup_entry()` explicitly uses exclusive, numbered claims for this reason (`tools/setup.py:1311-1332`). Preserve that pattern; do not reuse its move operation, since these instruction files need copy-before-write semantics.

- **MEDIUM — The doctor applier’s result will not refresh the displayed row or expose its detailed output.**  
  The plan returns only `{"ok": ok, "lines": lines}` (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:137`). The doctor UI updates a successful row only from `current_display` or `after` (`tools/config_doctor_app.py:222-243`); failures display `reason`, not `lines` (`:107-115`). Consequently, a successful rewrite can leave “installer wording” visible, while a failure hides the useful explanation. Direct row/applier tests at plan line 138 will not catch this UI-contract mismatch.

- **MEDIUM — Per-file I/O failure behavior is underspecified.**  
  The plan defines backup failure handling but no explicit read-error status or target-write failure policy (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-03-PLAN.md:106`). `build_catalog()` invokes cross-row reads without an exception boundary (`tools/config_doctor_checks.py:1067-1071`), so an unreadable instruction file could abort the catalog. Existing readers deliberately distinguish absent, unreadable, and valid data (`tools/config_doctor_readers.py:156-176`). The new path should similarly report uncertainty and continue inspecting the other hosts, not mislabel an unrecognized block as “ai-kit wording.”

##### Suggestions
- Test `_build_wizard_context()` and the housekeeping rebuild with zero, one, and two hosts. Verify the item and previews survive the full route to Review.
- Carry the reviewed change set—or equivalent approved path/content identity—into confirmation. Refuse newly discovered or changed targets until reviewed again.
- Claim backup names exclusively, handle collisions, and add fixed-clock/concurrent-attempt tests plus backup/write-failure injection.
- Return the doctor’s existing display and error fields, and test confirmation through the UI contract.
- Specify per-file unreadable/write-failed outcomes, temporary-file cleanup, and continuation to remaining hosts.

##### Risk Assessment
**HIGH.** This plan writes global instruction files. The narrow byte edit is sound, but reviewed-scope protection and non-overwriting backups are necessary safety properties, and the wizard integration currently omits a real selection-rebuilding path.

#### Overall Assessment

**Status: Issues Found — revise before execution.**

Coverage is complete: **30-01, 30-02, and 30-03** each reviewed. The changes are largely required by locked decisions; I would not remove the queue, shared marker editor, lenses, or full feature scope in pursuit of a smaller diff. The smallest complete correction is to finish the existing locking, fixture, wizard-context, confirmation, and backup contracts—not introduce another orchestration layer.

No files were changed and no tests, builds, indexing, or interactive UI checks were run. Findings are source-grounded; runtime timing and third-party-tool behavior remain unverified in this review.

### Batch B (30-04, 30-05)

Using **ai-kit-spec-review-checklist** and **ponytail** to review only 30-04 and 30-05 against the source and locked decisions. I’ll keep this read-only and won’t run test suites.


#### 30-04

##### Summary

The plan has a sound division of responsibility: reuse 30-01’s index engine, keep brief generation separate, and let the adapters deliver the result. Its atomic-write and fake-tool approach fits the repository. However, it is **not ready to execute unchanged**: checkout identity is not enforced, the provisional `--next` brief contradicts its own consumption rule, and the planned codegraph parser assumes an output format that the installed CLI does not consistently produce.

##### Strengths

- **[ponytail] Appropriate reuse of the atomic-write pattern.** The text writer specified in `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:125` follows `skills/ai-kit-commit-fold/scripts/flow_record.py:112–127`: temporary file in the destination directory, flush/fsync, replace, and cleanup on failure. A small text variant is justified; a new persistence abstraction is unnecessary.
- **The CLI and documentation changes are paired correctly.** The dispatch registration and SKILL.md bullet at `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:127–129` account for `tests/test_flow_docs.py:122–129`, which derives required documented commands directly from `_FLOW_HANDLERS`.

##### Concerns

- **HIGH — The selected unit is not bound to the checkout being indexed.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:126` specifies refreshing the supplied checkout but no branch-identity check. Existing selector resolution in `skills/ai-kit-commit-fold/scripts/fold.py:310–334` only constructs unit metadata; it does not switch or validate HEAD. Consequently, selecting B while checked out on main could refresh main and write a B-stamped brief. The existing checkpoint command explicitly rejects this situation at `skills/ai-kit-commit-fold/scripts/flow_unit.py:239–241`. Also cover the successful “joins hotfix” start path: `_start` can return a joined unit different from the requested unit at `skills/ai-kit-commit-fold/scripts/flow_unit.py:192–195`.

- **HIGH — The provisional planning brief tells its intended reader to ignore it.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:118` requires `unit: next (no unit yet)`, while line 125 requires readers to ignore a brief whose unit is not theirs. The pre-plan consumer necessarily has no recorded unit matching that stamp. This conflicts with the locked delivery requirement in `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-CONTEXT.md:81–85`. File existence alone will not prove that the plan writer can use the brief.

- **HIGH — The codegraph parser and fake omit real output variants and truncation.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:106` and line 164 prescribe parsing headers containing `name(kind)` items. The installed CLI delegates to the MCP handler—`~/.codegraph/versions/v1.6.2/lib/dist/bin/codegraph.js:1273–1279`—whose focused headers contain **bare names** and a rendering annotation, not `name(kind)` items (`.../lib/dist/mcp/tools.js:5824–5845`). Whole-file headers also cap names and append `+N more` (`.../lib/dist/mcp/tools.js:5981–5990`). The planned fake emits only the simple variant. Ordinary large files can therefore lose searchable names without triggering the nonzero-exit fallback, while tests remain green.

- **MEDIUM — Git pathname parsing is not safe for the general-project contract.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md:125` uses line-oriented `git diff --name-status -M`, and line 164 uses line-oriented `git ls-files`. Git can quote non-ASCII names and escape tabs/newlines, so the parsed paths need not identify real files; rename parsing is particularly vulnerable. **[ponytail]** Existing code already demonstrates the correct NUL-delimited pattern in `skills/ai-kit-commit-fold/scripts/fold_engine.py:217–227` and `skills/ai-kit-commit-fold/scripts/flow_stack.py:180–189`.

##### Suggestions

- Before refreshing or writing, validate the effective unit against the checkout using the existing branch/ref helpers. Test a wrong-branch invocation and the hotfix-join start path.
- Define an explicitly usable provisional-brief state for `--next`, while retaining rejection of genuinely foreign-unit briefs. Test the consumption rule, not just the stamp.
- Support actual codegraph header variants and visibly label partial/truncated name discovery. Extend the fake with focused, capped, and successful-but-unparseable output.
- Use `-z` for both Git listings and preserve literal names through rendering and searching. Add non-ASCII, tab-containing, and renamed-path fixtures.

##### Risk Assessment

**HIGH.** The main risks are incorrect or silently incomplete information reaching downstream agents. The proposed happy-path tests do not currently distinguish those failures from a valid brief.

#### 30-05

##### Summary

The advisor slice largely fits the existing architecture: it can reuse the current lexer, frequency counters, deduplication, state lock, and hook writer. The setup slice has a more serious gap: its fail-open promise does not cover the complete Make target or Python exception paths. The search classifier and installer fixtures also contain concrete inconsistencies that should be resolved before implementation.

##### Strengths

- **[ponytail] Existing advisor state machinery covers the new advice ID.** The integration proposed in `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-05-PLAN.md:104` can reuse `count_due`, call-key deduplication, and `with_state` in `tools/hooks/advisor_core.py:332–381` and `393–455`. No separate counters, cache, or locking implementation is needed.
- **The hook matcher can migrate through the existing writer.** The one-row change at `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-05-PLAN.md:105` is supported by `tools/setup.py:1983–2011`: it moves only the owned hook object when its matcher changes, preserving neighboring user hooks. The plan also names the existing matcher assertions that must change.

##### Concerns

- **HIGH — The advertised fail-open behavior does not cover the whole setup path.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-05-PLAN.md:137` makes `setup-dev` depend on `setup-env`, whose unguarded `uv sync` recipe is at `Makefile:30–31`, then ends with another unguarded `uv run pre-commit install`. A fresh offline environment can fail before the guarded installer script runs. Separately, the algorithm at plan line 136 handles return codes but specifies no handling for `TimeoutExpired`, execution/permission errors, or lock-file failures. `check=False` does not turn those exceptions into return codes. This does not satisfy the required network/permission/package-manager degradation at `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-SPEC.md:265–269`.

- **MEDIUM — Markdown-only classification contradicts the required examples.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-05-PLAN.md:104` considers a search Markdown-only only when **every** scope token is Markdown-like. But the required `rg foo docs --glob '*.md'` example at line 94 supplies both `docs` and `*.md`; the directory token makes that predicate false even though the positive glob restricts the search to Markdown. Likewise, Grep with `path: tools` and `glob: "*.md"` would be misclassified. A negative glob such as `!*.md` must not be interpreted as a positive Markdown restriction.

- **MEDIUM — Index detection follows directory ancestry rather than the searched checkout.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-05-PLAN.md:104` walks to the filesystem root looking for any `.codegraph/`, without stopping at a nested repository/worktree boundary or resolving an explicit search target. An unindexed worktree nested below the indexed main checkout will therefore be called indexed—the exact parent-index ambiguity documented in `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-SPEC.md:39–41`. Searches targeting another repository can receive the same false claim.

- **MEDIUM — The installer fixture cannot exercise the specified missing-gh path.**  
  `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-05-PLAN.md:127` pre-populates PATH with a fake `gh`, but line 136 defines gh presence using `shutil.which`. That makes gh present before `brew install gh`, so the required installer order and failed-brew scenario cannot occur as written. The same fixture says the second run calls no installer, although codegraph remains absent and the algorithm retries missing tools. These are contradictory test expectations, not evidence of idempotency.

##### Suggestions

- Make the complete `setup-dev` orchestration report recoverable provisioning failures and continue, including environment setup and hook installation. Preserve strict behavior for the existing `setup-env` and `dev` targets.
- Handle installer exceptions per tool, continue to later tools, and test timeout, permission failure, failed environment setup, and failed hook installation.
- **[ponytail]** Keep the existing `_command_tokens` / `_command_words` lexer (`tools/hooks/advisor_core.py:76–150`). Add only bounded option interpretation that distinguishes search roots, positive filters, and exclusions; do not build a general shell parser.
- Stop index discovery at repository/worktree boundaries using filesystem checks, and evaluate explicit search paths where available.
- Have fake brew create fake gh only after installation succeeds. Define second-run behavior as “no successful tool is reinstalled”; explicitly allow retrying the failed tool rather than adding unnecessary persistent failure state.

##### Risk Assessment

**HIGH.** The advisor issues mainly create noisy or inaccurate advice. The setup issue breaks a central resilience requirement on fresh or constrained machines, and the proposed fixture would not currently prove that requirement.

##### Overall status

**Issues Found — revise both plans before execution.** Coverage: **2/2 plans reviewed**. Dependency plans were read only for interfaces and handoffs; their future implementations were not treated as existing source.

No files were changed and no test suites or installers were run. Runtime behavior and timing remain unverified; this review is source-based.

### Batch C (30-06, 30-07)

Using **ai-kit-spec-review-checklist** and the **ponytail** lens to review 30-06 and 30-07 against the source. I’ll keep this read-only and won’t run tests.

##### Document type
GSD · implementation plans. Both requested plans were reviewed against repository source and the relevant dependency contracts.

#### 30-06

##### Summary
The plan uses the existing command router, GSD skill-resolution mechanism and dogfood-check seam appropriately. However, delivery is incomplete outside ai-kit’s own config and on GSD’s existing cross-AI execution path. Its proposed GSD fixture also conflicts with the wave-one skip rule. These gaps should be resolved before execution; successful hook rendering alone would not establish the phase’s end-to-end guarantees.

##### Strengths
- **Reuses the existing security boundary.** The proposed verbs extend the fixed dispatch table rather than introducing shell execution. Existing `parse()` validates the verb and phase, and `route()` invokes Python through `spawnSync` with an argv array (`skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/ai-kit-fold.cjs:33–43`, `:68–91`; [30-06-PLAN.md:109](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L109)).
- **The contribution mechanism is source-grounded.** The installed validator accepts inline contributions and validates their destination role; the planning workflow explicitly injects planner-targeted `fragment.inline` text (`.claude/gsd-core/bin/lib/capability-validator.cjs:3025–3062`, `:3125–3134`; `.claude/gsd-core/workflows/plan-phase.md:856`).
- **[ponytail] The drift check extends an existing seam.** `_run_gsd`, `FlowRun` and `_check_point` already provide subprocess isolation and named drift reporting, so the plan does not need another checking framework (`tools/check_dogfood.py:252–258`, `:300–319`; [30-06-PLAN.md:110](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L110)).

##### Concerns
- **HIGH — General GSD projects never receive the brief wiring.** The only installation of the three `.aikit/brief` entries is the write to **this checkout’s** `.planning/config.json`; the fixture explicitly supplies equivalent configuration itself ([30-06-PLAN.md:133–142](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L133)). Installing the shipped capability registers commands and hooks, but its manifest has no agent-skills configuration (`skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/capability.json:11–17`). The existing general installation instructions also contain no brief-wiring step (`skills/ai-kit-commit-fold/SKILL.md:129–138`). Consequently, another project can generate the brief without handing it to its agents, despite R5 being general (`.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-SPEC.md:159–166`).

- **HIGH — Cross-AI execution bypasses both the new wave hook and executor skill injection.** The plan adds its execution boundary at `execute:wave:pre` and delivers the brief through `gsd-executor` agent-skills ([30-06-PLAN.md:108](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L108), [30-06-PLAN.md:137](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L137)). But GSD delegates cross-AI plans **before** entering `execute_waves`; successful delegated plans are removed from that wave list (`.claude/gsd-core/workflows/execute-phase.md:437–446`). Their prompt is composed from objective, tasks and PROJECT.md—not the executor’s agent-skills block (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:82–87`, `:122–124`). Thus `--cross-ai` can execute the first task before the execution boundary and without the brief.

- **HIGH — The proposed dispatch fixture already represents completed wave one.** Task 1 expects `boundary-wave` to write `point: wave`, and Task 2 relies on that command creating the included brief ([30-06-PLAN.md:101–111](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L101), [30-06-PLAN.md:133](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L133)). However, `_fixture()` calls `gsd_project()` without `summary=False` (`tests/test_ai_kit_commit_fold_e2e.py:47–52`), whose default creates a SUMMARY (`tests/fold_fixtures.py:164–176`, `:185–202`). Plan 04 explicitly treats missing `wave:` as wave one and skips the boundary when those summaries exist ([30-04-PLAN.md:192–201](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-04-PLAN.md#L192)). Following both plans literally therefore takes the skip branch, not the expected write branch.

- **MEDIUM — Missing-brief reporting reaches the wrong set of agents.** The persistent fallback lives in the lens brief, which is attached to six lens agents; only the planner overlaps with the three required brief consumers. The researcher and executor receive no persistent fallback when `.aikit/brief/SKILL.md` is missing, while five lens-only agents are told to report a missing brief they were never configured to receive ([30-06-PLAN.md:137–139](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L137)). GSD drops a missing project-relative skill rather than substituting fallback content (`.claude/gsd-core/bin/lib/init.cjs:3917–3939`). The proposed negative test checks only the planner, so it misses both problems.

- **MEDIUM — `live-lenses: ok` does not establish that ponytail can load.** The live check accepts the emitted lens line and absence of warnings ([30-06-PLAN.md:142](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-06-PLAN.md#L142)). For namespaced ponytail entries, GSD emits a Skill-tool directive without checking whether the plugin exists (`.claude/gsd-core/bin/lib/init.cjs:3872–3882`, `:3947–3953`). An unavailable ponytail plugin therefore passes this check. The removed-lens fixture exercises bare `impeccable`, not this distinct failure mode.

##### Suggestions
- Add brief wiring to the **general GSD installation path**, preserving each project’s existing agent entries. Test installation without manually preconfiguring the fixture.
- Cover delegated execution through an ai-kit-controlled integration point: prove the boundary runs before the external command and its prompt includes the brief, without editing installed GSD.
- Use an unfinished fixture for boundary dispatch; separately assert that completed wave one skips and interrupted wave one reruns.
- Deliver missing-brief instructions to all three `BRIEF_AGENTS`, conditional on the current agent’s role.
- Label the existing live check as **render/wiring verification**, or supplement it with an explicit host-side plugin-load check.

##### Risk assessment
**HIGH.** The core router changes are small and well constrained, but the plan can pass configuration/render checks while missing real execution paths. Its principal fixture also contradicts the dependency’s specified behavior.

#### 30-07

##### Summary
The adapter changes are appropriately small: reuse the shared boundary command and add brief instructions to existing native and external dispatch guidance. The main unresolved issue is the pre-planning route. An instruction introduced by an execution-only adapter cannot ensure that a plan writer, which has already finished, received the brief—especially in another project. The plan also duplicates an existing executable start-block test.

##### Strengths
- **Preserves existing start/refusal handling.** The new boundary line follows the successful `start` command and does not replace the fold-skill lookup or the plan-presence check (`skills/ai-kit-spec-execute-superpowers/references/start-step.md:17–34`; [30-07-PLAN.md:70](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L70)).
- **Uses the correct external-prompt integration point.** The existing Compose section places implementer work inside `<objective>`, which the runner uses for its task digest. Adding the brief instruction there preserves that established contract (`skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:37–52`; [30-07-PLAN.md:71–72](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L71)).
- **[ponytail] No second indexing implementation is introduced.** Both dispatch modes point to the generated brief, while the start block calls the same shared `fold.py boundary` command ([30-07-PLAN.md:70–72](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L70)).

##### Concerns
- **HIGH — The pre-planning handoff remains unresolved and is not generally delivered.** The plan explicitly marks its instruction-file fallback as “flagged for owner confirmation,” yet remains autonomous ([30-07-PLAN.md:12](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L12), [30-07-PLAN.md:61](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L61)). The referenced instruction-file change is to **ai-kit’s own AGENTS.md** ([30-02-PLAN.md:115–120](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-02-PLAN.md#L115)); it does not reach another project’s superpowers plan writer. The execution adapter is demonstrably late: its start reference says the spec and plan are already committed (`skills/ai-kit-spec-execute-superpowers/references/start-step.md:6–10`). The only runnable acceptance test covers execution start and wave refresh, not pre-planning delivery ([30-07-PLAN.md:100](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L100)). R1 and R5’s general pre-planning guarantee therefore remains unproven.

- **MEDIUM — [ponytail] `TestStartBlockRuns` duplicates an existing executed-block harness.** The proposed new class extracts the fenced block, fills its placeholders, constructs an isolated fold installation and runs Bash ([30-07-PLAN.md:100–105](.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-PLAN.md#L100)). `TestStartStep.setUp()` and `_run()` already perform those operations, and its successful-start test already supplies a bare remote (`tests/test_ai_kit_spec_superpowers.py:2920–2953`). A second harness adds fixture setup and maintenance without testing a different entry point.

##### Suggestions
- Resolve the owner-confirmation item before autonomous execution. Define a concrete pre-planning entry point that target-project sessions actually load, including fold-script discovery and the plan-writer brief handoff.
- Add a fixture proving the sequence **boundary → writer receives brief → plan creation**, rather than only asserting that execution documentation mentions it.
- Extend `TestStartStep` with the wave stamp, fake-tool cwd, no-`.planning/` and unchanged-main assertions instead of adding another block-execution harness.

##### Risk assessment
**HIGH for full requirement completion; LOW for the proposed execution-time edits themselves.** The shared-command approach is sound, but the before-planning guarantee is still an unresolved integration decision.

##### Overall disposition
**Changes requested.** Both plans were covered. Prioritize general-project delivery, cross-AI execution coverage and the completed-wave fixture conflict before execution.

No files were changed and no tests were run. Findings are based on source tracing; plan 01/02/04 mechanisms were assessed as dependency contracts, not as completed implementations.


---

## OpenCode Review (referee-two)

Not run: the probe failed with `Error: Model grok-cli/grok-4.7-xhigh is unavailable` (89 s, exit 1).

---

## OpenCode Review (referee-three)

Not run: the probe failed with `Error: Model anthropic/claude-opus-5-5-xhigh is unavailable` (88 s, exit 1).

---

## Plan coverage

- 30-01: referee-one (batch A), own section, `file:line` evidence.
- 30-02: referee-one (batch A), own section.
- 30-03: referee-one (batch A), own section.
- 30-04: referee-one (batch B), own section.
- 30-05: referee-one (batch B), own section.
- 30-06: referee-one (batch C), own section.
- 30-07: referee-one (batch C), own section.

No batch is uncovered. referee-two and referee-three covered no plan.

## Consensus Summary

One reviewer (referee-one) covered all seven plans, so there is no cross-reviewer consensus. The orchestrator checked
each finding against the plan text, the installed GSD workflows (`.claude/gsd-core/workflows/`, `.claude/hooks/`) and
the source, and asked jev-fast-decision for an advisory classification of the batch A and B findings (one call, 17
items, TypeSafe backend). Every answer came back `needs_fallback` (16 `supported`, 1 `partial`, confidence 0.17 to
0.51), so the verdicts below are the orchestrator's. Findings that repeat across batches are merged.

Orchestrator checks run during triage: the installed `codegraph explore` (1.6.2) prints per-file header lines of the
form `` **`path`** — name(kind), ... +N more `` with kinds such as `calls` and `instantiates` and about six names per
file; `codegraph status --json` carries `pendingChanges`, `worktreeMismatch` and `index.reindexRecommended`;
ai-kit's `graphify-out/graph.json` carries `built_at_commit`; GSD's rebuild runner writes its pid into
`.planning/graphs/.rebuild.lock` and then runs `graphify update .` into the same `graphify-out/`
(`.claude/hooks/lib/gsd-graphify-rebuild.sh:24-35`); `tests/test_flow_contract.py:72`, `tests/test_flow_stack.py`
and `tests/test_ai_kit_commit_fold_e2e.py:402` replace PATH with `host_fakes.host_path(bin)`, whose default base is
the process PATH (`tests/host_fakes.py:68-70`); the housekeeping path rebuilds the selection without extra items
(`tools/setup.py:3862-3866`, `tools/wizard_app.py:1056-1061`); cross-AI delegation runs at execute-phase step 2.5,
before `execute_waves` (`.claude/gsd-core/workflows/execute-phase.md:437-446`), from the plan's `<objective>` and
`<tasks>` plus PROJECT.md (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:82-87`).

GSD hook facts that bound every fix (verified, unchanged): `plan:pre` dispatches `ref.skill` and `ref.agent` only,
no `ref.command` (`.claude/gsd-core/workflows/plan-phase.md:512-515`), and injects planner contributions by
`fragment.inline` (`plan-phase.md:856`); `execute:wave:pre` dispatches contributions and steps and evaluates no gate
(`.claude/gsd-core/workflows/execute-phase.md:616-626`); `discuss:pre` applies every hook per
`loop-hook-dispatch.md`, whose step arm runs `gsd_run ${ref.command} --phase N --raw`
(`.claude/gsd-core/workflows/discuss-phase.md:297-300`, `.claude/gsd-core/references/loop-hook-dispatch.md:34-55`);
`verify:post` runs before the verifier writes VERIFICATION.md
(`.claude/gsd-core/workflows/execute-phase/steps/verify-phase-goal.md:39-45`).

### Agreed Strengths

Single reviewer; no agreement to report. referee-one credits the reuse of `flow_record.common_dir`/`render`, the
detached launch with an inherited lock fd, the real `gsd-tools graphify status` check, the byte-level marked-block
edit, the fixed-verb router, the contribution mechanism and the shared-command superpowers changes.

### Agreed Concerns

Single reviewer; see the confirmed lists below.

### Divergent Views

None (single reviewer).

## Current HIGH Concerns

1. **30-01: the GSD rebuild lock is checked only after the build.** `graphify_step` builds, then waits on
   `.rebuild.lock` before the copy (30-01-PLAN.md:198); GSD's runner holds that lock while building into the same
   `graphify-out/`. Needed: in a GSD project wait for the lock before `graphify update .`, re-check it before the
   copy, and state the remaining race (GSD may start after the check; its hook is not ours to edit).
2. **30-01: queued worktrees can be stranded behind a foreground lock holder.** `detach` starts a runner only when it
   takes the lock (30-01-PLAN.md:233); bare `index` and `boundary` hold the same lock and never drain
   (30-01-PLAN.md:234, 30-04-PLAN.md:126). Needed: every lock holder starts the detached runner on release when the
   queue is non-empty, tested without a manual `--drain`.
3. **30-01: existing callers drop the fake-tool PATH.** `git_env` prepends the fakes (30-01-PLAN.md:160), but
   `tests/test_flow_contract.py:72`, `tests/test_flow_stack.py` and `tests/test_ai_kit_commit_fold_e2e.py:402`
   replace PATH with `host_fakes.host_path(bin)`, whose base is the process PATH. Needed: pass the fixture PATH as
   the base at every such call and add those modules to the plan.
4. **30-01: an old or empty graph can be recorded as a fresh build.** The check accepts any non-empty JSON object
   (30-01-PLAN.md:161) before writing `ok` for HEAD (30-01-PLAN.md:198). Needed: require `built_at_commit` equal to
   HEAD and a `nodes` list, else the `wrote no graph` path, with a stale-graph case and a `{}` case.
5. **30-03: the wizard item can vanish.** The item is added in one selection builder and its previews live in a
   per-host `WizardModel.meta` (30-03-PLAN.md:159); housekeeping rebuilds the selection without it
   (`tools/setup.py:3862-3866`) and the zero-host pane gets `meta={}` (`tools/wizard_app.py:324`). Needed: one
   helper used by both builders, previews in component-level context, tests over zero, one and two hosts and the
   housekeeping route.
6. **30-03: confirm is not bound to the reviewed diffs.** Review shows `plan_changes(env)`, confirm calls
   `apply(rules_env, dry)` which plans again (30-03-PLAN.md:106,159-166). Needed: confirm applies only the reviewed
   change set and skips, with a note, any file whose bytes differ from the reviewed `before` or that was not reviewed.
7. **30-04: the boundary is not bound to the checkout's branch.** Nothing checks HEAD against the unit's branch
   (30-04-PLAN.md:126), unlike `_checkpoint`'s `ref_mismatch` (`flow_unit.py:239-241`); `start` can succeed by
   joining a hotfix unit (`flow_unit.py:192-195`). Needed: refuse `ref_mismatch` for a recorded unit whose branch is
   not HEAD, and brief the effective (joined) unit at start.
8. **30-04: codegraph explore names are silently truncated.** The parser and fake assume `name(kind)` with function,
   method and class kinds only (30-04-PLAN.md:106,164); the installed CLI lists about six names per file with kinds
   like `calls` and a `+N more` tail. Needed: accept any kind, label the names line as partial with the dropped
   count, and make the fake print the capped form.
9. **30-04: the `--next` brief tells its reader to ignore it.** It is stamped `unit: next (no unit yet)`
   (30-04-PLAN.md:118) while every brief says to ignore one not naming the reader's unit (30-04-PLAN.md:125).
   Needed: a `next` stamp text that says it is for whoever writes the next unit's plan.
10. **30-05: `setup-dev` is not fail-open.** `setup-dev: setup-env` runs an unguarded `uv sync` and an unguarded
    `uv run pre-commit install` (30-05-PLAN.md:137, `Makefile:30-31`); `run` handles exit codes but not
    `TimeoutExpired`, `OSError` or a lock-file error (30-05-PLAN.md:136). Needed: the script runs env sync and hook
    install as guarded steps, catches those exceptions per tool, always exits 0; `setup-env` and `dev` unchanged.
11. **30-06: the dispatch fixture has wave 1 finished.** `_fixture` builds plan 01 with its SUMMARY
    (`tests/test_ai_kit_commit_fold_e2e.py:47-52`, `tests/fold_fixtures.py:172`), so plan 04's wave-1 rule skips
    `boundary-wave` and the `point: wave` assertions (30-06-PLAN.md:101,133) cannot pass. Needed: an unfinished
    fixture (`summary: False`) for dispatch, plus the skip case on the finished one.
12. **30-06: cross-AI delegated plans miss the wave boundary and the brief.** Delegation runs before
    `execute_waves` and builds its prompt from `<objective>`/`<tasks>` plus PROJECT.md, not agent-skills. Needed:
    the planner contribution has each plan's `<objective>` carry the unit-brief line, and the commit-fold SKILL.md
    orchestrator list runs `ai-kit-fold boundary-wave` before an execute-phase run that delegates.
13. **30-06: other GSD projects never get the brief wiring.** Only ai-kit's config gets `.aikit/brief`
    (30-06-PLAN.md:137-142); the manifest carries no agent-skills and the SKILL.md install section has no wiring step,
    while R5 is general. Needed: a documented install step that appends `.aikit/brief` to the three agents' existing
    lists through `config-get`/`config-set`, and a fixture test that follows it instead of pre-supplying the arrays.

## Current Actionable Non-HIGH Concerns

- 30-01 (MEDIUM): write ignore entries to `flow_record.common_dir(top) / "info" / "exclude"` (the
  `_ensure_ignored` pattern), not a relative `--git-path` result (30-01-PLAN.md:196).
- 30-01 (MEDIUM): the e2e registers a cleanup that waits for the detached runner (takes the index lock with a
  deadline) before the temp repo is removed, also on assertion failure (30-01-PLAN.md:226,236).
- 30-01 and 30-02 (MEDIUM): GSD honors `graphify.graph_path` (`.claude/gsd-core/bin/lib/graphify.cjs:378-399`);
  when it is set, skip the `.planning/graphs/` copy with a `graphify-out only (graphify.graph_path is set)` line, and
  the rule and runbook name `.planning/graphs/` as GSD's default location, copied only with `graphify.enabled`.
- 30-02 (LOW): state the design-rule order check as `bullet_offset < marker_offset` (30-02-PLAN.md:152).
- 30-02 and 30-07 (MEDIUM, reviewer HIGH): the superpowers before-planning route is only ai-kit's own AGENTS.md
  sentence with a bare `fold.py` (30-02-PLAN.md:116, 30-07-PLAN.md:61). Name the script path the way start-step.md
  resolves it, state in both plans that target projects get the route with Phase 45.1's generated rules (RULE-03),
  and keep the owner-confirmation item as a recorded user-owned item, not a stop.
- 30-03 (MEDIUM, reviewer HIGH): claim backup names exclusively (`O_EXCL`, numbered suffix), like
  `_backup_entry` (`tools/setup.py:1311-1332`), with a fixed-clock collision test.
- 30-03 (MEDIUM): the doctor applier returns `current_display` (or `after`) on success and `reason` on failure
  (`tools/config_doctor_app.py:107-115,222-243`), not only `lines`.
- 30-03 (MEDIUM): an unreadable file gets status `unreadable` and a write failure a per-file failed line; the run
  continues with the other hosts and the doctor read never raises.
- 30-04 (MEDIUM): read `git diff --name-status -M -z` and `git ls-files -z` (the `fold_engine.py:217-227` pattern),
  with a non-ASCII rename fixture.
- 30-05 (MEDIUM): positive filters (`-g`/`--glob`, `-t`/`--type`, `--include`, `-name`/`-iname`, Grep `glob`/`type`)
  decide Markdown-only when present; a negated glob never counts; path scopes decide otherwise
  (30-05-PLAN.md:94,104).
- 30-05 (MEDIUM): `indexed_checkout` stops at the first directory holding `.git` (file or dir) and is true only when
  that directory holds `.codegraph/`.
- 30-05 (MEDIUM): the fixture's fake `brew install gh` creates the fake `gh`; the second run retries only the failed
  tool (30-05-PLAN.md:127).
- 30-06 (MEDIUM): the researcher and executor get the missing-brief instruction too (the lens brief's unit-brief
  section, or the lens-brief entry in their lists), worded for the three brief agents only, with a test per agent.
- 30-06 (MEDIUM): label `live_lenses.sh` as a render and wiring check; it does not prove the ponytail plugin loads.
- 30-07 (MEDIUM): extend the existing `TestStartStep` harness (`tests/test_ai_kit_spec_superpowers.py:2917-2953`)
  instead of adding `TestStartBlockRuns`.

## Not Actionable

- 30-02: R07 stays inactive for a project with the codegraph CLI but no `.codegraph/`. FLOW-06 asks the house rules to
  say to explore with codegraph "when it is indexed", which R07's `.codegraph/` condition matches; the rule text
  itself tells agents to run `codegraph init -y` when the CLI is present. Rejected (jev: supported, needs_fallback).

## Cycle summary

```yaml
cycle: 1
reviewers_ok: [referee-one]
reviewers_failed:
  referee-two: "Error: Model grok-cli/grok-4.7-xhigh is unavailable"
  referee-three: "Error: Model anthropic/claude-opus-5-5-xhigh is unavailable"
batches_uncovered: {}
high: 13
actionable_non_high: 15
not_counted: 1
open_conflicts: 0
plan_coverage_incomplete: []
```
