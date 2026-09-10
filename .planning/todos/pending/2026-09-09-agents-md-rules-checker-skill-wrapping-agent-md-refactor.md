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

3. **Commit hygiene**: any commits made during a plan/tasks/wave execution must be
   compacted into as few logically-grouped commits as possible.

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

7. **CodeGraph awareness**: encourage `codegraph_explore` MCP tool use for codebase
   exploration; recommend `codegraph init -i` when entering a workspace with no existing
   `.codegraph/` index, and `codegraph sync` after code changes.

## Solution

TBD — scaffold via `/superpowers:writing-skills`, evaluate with `/skill-judge`, then run
`/naming-analyzer` to pick the final skill name before wiring it as a wrapper around
`/agent-md-refactor`.
