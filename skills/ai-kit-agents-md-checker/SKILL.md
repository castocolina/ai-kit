---
name: ai-kit-agents-md-checker
description: Use when an AGENTS.md or CLAUDE.md agent-instruction file needs checking against ai-kit's own 17-rule house ruleset, or when a repo's Makefile target shape (setup-env, per-hook 1:1 targets, validate chaining, test pyramid) needs auditing for gaps. Flags each missing Makefile target or house rule individually, with a per-language tool recommendation sourced from live detection or a staleness-checked research cache, never invented from training data.
---

<!-- Directory/package name "ai-kit-agents-md-checker" is PROVISIONAL pending
     /naming-analyzer (Phase 6 Plan 03). Do not assume this is the final name. -->

# ai-kit-agents-md-checker

This skill is under active construction across Phase 6's three plans. Plan
01 (this commit) lands the scaffold plus the two deterministic checkers
(Makefile target-shape, workflow-rule prose). Plan 02 adds the remediation
payload and research-subagent cache fill. Plan 03 adds `/skill-judge` review
and the final `/naming-analyzer` rename. Full usage narrative lands with
Plan 02.
