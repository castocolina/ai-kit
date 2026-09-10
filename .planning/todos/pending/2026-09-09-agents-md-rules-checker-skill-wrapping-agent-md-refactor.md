---
created: 2026-09-10T00:43:39.014Z
title: AGENTS.md rules checker skill (wrapper for /agent-md-refactor)
area: tooling
severity: major
files:
  - ../gitig/.pre-commit-config.yaml
---

## Problem

Need a new skill that wraps `/agent-md-refactor` to check/enforce a set of house rules
for AGENTS.md-style agent-instruction files, beyond what plain refactoring covers today.

Build this skill (and the config skill in the companion todo) using the pipeline:
`/superpowers:writing-skills` → `/skill-judge` → `/naming-analyzer` (naming-analyzer picks
the final skill name).

Required rule content for the checker:

1. **English-only communication is mandatory.** The checker must call this out explicitly
   as a non-negotiable rule for agent instructions.

2. **Mandatory Makefile with a specific target shape**, independent of language:
   - `setup-env` — installs minimal local dev tooling accurate to the detected language(s)
     (node, python, go, java, rust): formatting, linting, code-smell, duplicate-code,
     dead-code, security, and other best-practice tools.
   - One Makefile target **per individual pre-commit hook**, 1:1 with the project's
     `.pre-commit-config.yaml` (reference: `../gitig/.pre-commit-config.yaml`, which
     partially does this today — it has the precommit file, but targets aren't broken out
     per hook). Goal: an agent that runs `make commit` and sees "5/7 hooks passed" can
     immediately re-run just the failed target instead of the whole battery.
   - A generic `validate` target that chains: all individual hook targets, in order,
     **lightest/cheapest checks first** (e.g. formatting before deep static analysis).
   - Rule: agents must not skip pre-commit checks, *except* to intentionally commit a
     failing/red test before then doing the work to turn it green (red→green TDD flow is
     the only sanctioned bypass).
   - Per-language tool conventions the checker should recommend/verify, e.g. formatting:
     go → gofmt, python → black, node → prettier or lint's own formatter, java → google-java-format
     (or similar) — same pattern extended to linting, dead-code, duplication, security scanners.
   - `test-unit` with `test` as an alias.
   - `test-integration`.
   - `e2e-test` where feasible — load a dockerized env if isolation is needed.
   - `arch-test` — component must have clear architecture with rails/tests that block
     agent-introduced architecture violations.
   - Every other validation/lint tool gets its own dedicated target.
   - Most validation targets should have a matching individual pre-commit hook target.

3. **Commit hygiene**: the compaction unit is **the plan**, across every plan/task-execution
   SDD framework (open-GSD, superpowers, OpenSpec, Spec Kit, or any other). Phase-level
   grouping (open-GSD) does not get its own separate compaction pass — going that coarse
   loses per-plan traceability. What must be avoided is commit sprawl within a single plan:
   a commit for one test file then another for the next, or a fix commit, then another fix,
   then another, as problems surface one at a time. Before closing out a plan, the agent
   must look back at what it actually committed and fold everything that is fully related
   (same plan, same concern) into as few logically-grouped commits as possible.

4. **Cross-AI review requirement for open-GSD plans**: every plan created must set
   `cross-ai: true` in its frontmatter so it gets validated by another LLM vendor/model.
   Preferred reviewers, in order: `*my-plan-review`, GLM-5.2 high (if available),
   chatgpt-5.6-sol high (if available), Opus as last resort.
   - Cross-AI execution should also be enabled to let *cheaper* models from other vendors
     execute already-reviewed, well-formed plans. This is an independent, mandatory rule
     (does not depend on the review rule). Fallback order: Haiku only if Claude is the only
     vendor available; otherwise prefer other cheap models available on PATH from
     cursor/opencode. Not just any cheap model qualifies — prefer models matching
     `*coding*` on router-env, or `deepseek-flash`, `composer`, `*-code`.
   - The generated cross-ai command itself must be **path-agnostic**: config.json checks
     must never bake in a full absolute path to an executable (e.g. a resolved venv/nvm/
     brew path picked up at generation time on one machine). Reference executables by bare
     command name, resolved via PATH at run time, so the config stays portable across
     machines/environments.

5. **rtk awareness**: if `rtk` (Rust Token Killer CLI proxy) is present on the system, the
   checker should advise agents on it and explain how it works (token-optimized proxy that
   filters bash output; hook-based transparent rewriting of commands like `git status` →
   `rtk git status`).

6. **Modern CLI tool awareness**: if tools like `rg`, `bat`, `sd`, `fd`, `eza`, etc. are
   present, agents must be told to prefer them and given a short usage explanation for each.

7. **CodeGraph awareness** (verified against installed v1.6.0, 2026-09-10 — re-verify if
   stale per rule 14): when `.codegraph/` is present, prefer the `codegraph_explore` MCP
   tool (and `codegraph_node` for a single symbol) over ad hoc Read/Grep for codebase
   exploration. Run `codegraph init` when entering a workspace with no index — **not**
   `init -i`; `-i`/`--index` is deprecated, indexing now runs by default on `init`. Manual
   `codegraph sync` is only needed when the file-watcher/daemon is disabled or a script
   needs a guaranteed-fresh graph — the daemon auto-syncs on save in normal interactive
   use. `.gitignore` is honored automatically; per-project overrides (force-include/exclude/
   deprioritize) go in an optional `codegraph.json`, not a bespoke ignore file. Scope
   awareness: CodeGraph indexes **code only** (30+ programming languages) — it does not
   index Markdown/docs and has no doc-to-code staleness detection; don't reach for it to
   verify whether a doc is stale (see rule 8's graphify note for that instead).

8. **Graphify awareness** (verified against installed v0.9.54, 2026-09-10 — re-verify if
   stale per rule 14): graphify and CodeGraph are not mutually exclusive — both can be
   present and useful at once, for different jobs. Graphify's primary interface is CLI +
   generated static output (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, plus optional
   exports), not an MCP tool — a `--mcp` stdio-server flag exists but isn't wired into this
   project's MCP config, so treat it as CLI-driven. Corrects a common misconception:
   graphify **does** honor `.gitignore`/`.git/info/exclude` by default, same as CodeGraph;
   `.graphifyignore` is only an *additional* override file that takes priority when
   `--no-gitignore` is explicitly passed, not a required substitute for `.gitignore`.
   - Standalone use (no GSD): output defaults to `./graphify-out/` at the run root;
     `graphify hook install` sets up a **git post-commit hook** that re-extracts and
     rebuilds the graph after each commit for *code* changes only — doc/image changes need
     a manual `graphify update` (or `--update`), the hook doesn't pick those up on its own.
   - GSD-managed use: output instead lands in `.planning/graphs/graph.json`; the enabling
     key is `graphify.enabled` in `.planning/config.json` (a capability flag, default
     `false` — **not** `workflow.graphify`), with a separate `graphify.auto_update` flag
     (default `false`) governing auto-rebuild. When `auto_update` is on, a Claude/host
     PostToolUse hook (not a git hook) fires `graphify update .` after HEAD-advancing git
     ops on the default branch. `gsd-planner`/`gsd-phase-researcher` both check graph
     freshness (`graphify status`) during planning/research and treat a stale/failed graph
     as approximate context rather than blocking — it's a per-invocation freshness check,
     not strictly tied to plan/wave/phase boundaries.
   - Doc value-add over CodeGraph: graphify's `detect()` step does categorize and
     semantically index documents (not just code) — `.md`/`.txt` docs, PDFs, images — into
     typed nodes (`document`/`rationale`/`concept`) with edges like `references`/`cites`,
     which is the closer fit for spotting a doc that's talking about since-changed code (see
     rule 11). Neither tool, as verified, ships a dedicated "this doc references a renamed/
     removed symbol" staleness alarm — graphify's doc/concept graph is the best lead
     available today, not a guarantee.
   - When `graphify` is present as a CLI (with or without GSD's `graphify.enabled`), the
     checker should have agents note that fact and explain how to use it if present —
     mirroring the CodeGraph rule's shape — but should not claim MCP-tool-equivalent
     integration it doesn't currently have on this host.
   - **Coexistence is the expected/default posture, not a special case** — the checker
     should tell agents to use both when both are present: CodeGraph for fast code-structure
     lookups, graphify for doc-aware indexing, per the split above.
   - **Agents must trigger indexing proactively, not rely on the hook alone.** The
     post-commit hook (standalone) or the `auto_update` HEAD-advance hook (GSD-managed) both
     assume merges to the default/main branch happen as part of the normal local workflow —
     that's not always true (e.g. local feature-branch work that doesn't merge to main
     often, or a branch merged remotely instead of locally). An agent that only relies on
     the hook can end up working against a stale graph without knowing it. So: run
     `graphify update` (or check `graphify status` and update if stale) directly after
     making non-trivial changes, rather than assuming the hook already covered it — same
     spirit as rule 14's "verify, don't assume" for stale knowledge, applied to the graph
     itself.
   - **When the repo is under open-GSD, target `.planning/graphs/`, not `./graphify-out/`.**
     If `.planning/` exists and GSD is managing the repo, agents should not run bare
     `graphify update .` and let it default to `./graphify-out/` — that produces a second,
     disconnected index GSD's own tooling never reads. Instead: confirm `graphify.enabled`
     is set in `.planning/config.json` (enable it if graphify is present and it isn't), and
     let GSD's own `graphify update` path write to `.planning/graphs/graph.json` — the same
     location `gsd-planner`/`gsd-phase-researcher` read from. Only fall back to the
     standalone `./graphify-out/` default when the repo genuinely has no GSD planning
     directory.

9. **No orphaned ephemeral processes/windows from e2e verification.** Any agent driving
   e2e verification that spawns ephemeral processes or windows — terminals, browsers, or
   anything under a hub/daemon process — must kill/stop what it spawned when done. No
   orphan processes left alive after the agent finishes.
   - **Known failure-class to be aware of, not to blame anyone for**: cross-AI subprocess
     tools can copy/extract their own runtime framework into a temp location on every
     invocation, and if the subprocess is killed/crashes instead of exiting cleanly, that
     copy is orphaned — nothing cleans it up. Observed concretely with opencode: on macOS
     it creates a per-invocation temp folder it copies its runtime framework into; on
     Linux, something underneath it (Bun) does the equivalent by copying native artifacts
     into temp on each run — possibly the same underlying mechanism wearing two faces. This
     is not opencode-specific in principle — it's a generic pattern for any subprocess CLI
     that self-extracts/copies its runtime per run, so the awareness needs to generalize:
     today it's opencode, tomorrow it could be a different framework or app entirely.
     - **Symptom, not cause**: an unexplained Bash-tool error, or a process dying outright,
       can be disk/partition exhaustion from this kind of orphaned-copy buildup rather than
       a bug in the task at hand. When space-related errors show up, check actual
       partition/disk free space and inspect the directories the project's prune scripts
       target — don't assume the failure is in the work being done.
     - Some of these tools expose a flag or env var to redirect where they copy to (e.g.
       Bun's transpiler cache path can be redirected off the default temp location) — worth
       checking whether the specific tool involved has that knob, rather than only relying
       on after-the-fact cleanup.
     - This project already has scheduled/background prune processes set up for this (see
       `./tmp/` for the local scripts, plus a `tools-installer` project counterpart) — but
       the checker's job is not to describe *how* those scripts work internally. It's to
       remind agents to stay alert: check whether such a scheduled cleanup process exists
       and is actually running for the current project/machine, and consider whether one
       needs to be set up if it doesn't — because the specific framework causing the leak,
       and whether an existing prune job still covers it, can both change over time.

10. **Ephemeral files land under `./tmp/` (gitignored), not scattered around the repo.**
   Scripts or files created just to check/probe something, with no lasting value as a
   project asset, must live under `./tmp/` — e.g. `./tmp/scripts/{kind}/`, `./tmp/docs/`.
   When a script turns out to be genuinely useful to the project, it graduates out of
   `./tmp/` into the conventional location for the stack: `./scripts`, `./tools`,
   `./src/main/scripts/`, etc., whichever matches the language/stack's own convention.
   - Documents sometimes need diagrams (not just simple flowcharts) embedded via Mermaid —
     use the `mermaid-diagrams` skill when a doc needs one.

11. **README/docs currency rule**: after adding, removing, or refactoring any significant
    feature, the README must be updated using the `crafting-effective-readmes` skill. This
    extends to every documentation surface that lives with the changed code, not just the
    top-level README: a submodule's own README and diagrams, javadocs, docstrings, JSDoc,
    etc. — all must be brought current, not just the root doc.
    - When the repo is `graphify`-indexed (graphify indexes documents too, not just code),
      prefer `graphify` over `codegraph` for this — its skills lean more on inference,
      which fits "what documentation is now stale after this refactor" better than
      codegraph's structural lookups. Sequence: refactor first, then run graphify's
      index-update skill, *then* update the stale docs found, then re-run the index update
      afterward if the doc edits themselves are worth re-indexing.

12. **No absolute paths in project assets, source, or tests.** Final code, tests, configs,
    and any other project asset must not hardcode absolute filesystem paths — they break
    the moment the user switches machines. Use relative paths, repo-root-relative
    resolution, or environment-provided roots instead.

13. **No excuse-driven deflection on failing tests or bugs — mandatory.** Never blame
    someone/something else for a failure, and never reach for phrases like "that's not my
    fault," "that's a scope change," "that will be deferred," or "that's not my problem" as
    a way to dodge a failing test or a bug. Every time a test fails or a bug surfaces, the
    agent must work out the best strategy to actually address it — pre-existing
    conditions are not an excuse to avoid the work. (Applies equally to bugs and to test
    failures.)

14. **Verify stale knowledge on gray-area/new topics instead of trusting training data.**
    Whenever a topic is a gray area, genuinely new, outside common sense, or plausibly
    post-dates or falls outside training data, the agent must research and fetch current
    online resources rather than answer from memory. Training data is stale by
    construction — check the current date/time and verify the recalled information is
    still accurate before relying on it.

15. **Theory → hypothesis → spike methodology for new/unfamiliar territory, before any
    plan.** For anything new (unfamiliar API, library, pattern, or the gray-area/new-topic
    case from rule 14), the mandatory sequence before writing a plan is: form a theory,
    state it as a testable hypothesis, then spike it — a small, throwaway script/probe
    (see rule 10's `./tmp/` convention) that actually checks the hypothesis against reality.
    Only once the spike confirms the approach works does planning/implementation proceed.
    No plans built on untested assumptions about new territory.

16. **No uncommitted files left in the working area when closing a plan.** Before a plan is
    considered closed, the agent must check the working area for uncommitted files. For
    each one found:
    - If it should be ignored (matches rule 10's `./tmp/` ephemeral case, or is otherwise
      not a project asset), gitignore it or move it under `./tmp/` rather than leaving it
      untracked in the working tree.
    - If it belongs to a task in the current plan (or a prior one), fold it into the
      appropriate commit per rule 3's compaction discipline — it should not be left
      dangling as an untracked/unstaged leftover.
    - If neither is clear, ask the user for confirmation rather than guessing (commit it,
      ignore it, or discard it) — do not silently leave it uncommitted and unexplained.

17. **No excess documentation — be concise, not narrative.** A common failure pattern: when
    a decision changes mid-development, agents narrate the abandoned path at length ("we
    did X instead of Y because Y was..."), spending verbose, repetitive prose on a road not
    taken that turned out insignificant. Don't. Documentation (READMEs, commit messages,
    PLAN/SUMMARY docs, code comments) should be concise: state what was done and why, with
    its actual advantages — skip the blow-by-blow of rejected alternatives unless the
    rejection itself carries a load-bearing lesson worth keeping (see the existing
    "why, not what" comment guidance this ties into). Keep prose tight; don't burn tokens
    retelling a history that didn't happen.

## Solution

TBD — scaffold via `/superpowers:writing-skills`, evaluate with `/skill-judge`, then run
`/naming-analyzer` to pick the final skill name before wiring it as a wrapper around
`/agent-md-refactor`.
