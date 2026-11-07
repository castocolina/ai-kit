---
phase: quick-261106-ua8
plan: 01
subsystem: setup wizard, skills frontmatter
status: complete
tags: [wizard, frontmatter, skills]
key-files:
  modified:
    - tools/setup.py
    - tools/wizard_app.py
    - skills/ai-kit-project-rules-agents/SKILL.md
    - skills/ai-kit-project-rules-cicd/SKILL.md
    - skills/ai-kit-project-rules-docker/SKILL.md
    - tests/test_setup.py
    - tests/test_wizard_app_1.py
    - tests/test_ai_kit_project_rules_agents.py
    - README.md
commits: [a9f6b67]
---

# Quick task 261106-ua8 summary

- **One reader (a9f6b67):** `setup._read_frontmatter` returns every top-level scalar folded to one
  line: plain, double-quoted (YAML escapes decoded through `json.loads`), single-quoted (`''`),
  multi-line and `|`/`>` block values, comment lines skipped. `_read_component_desc` caps its
  `description`. It matches PyYAML on name and description for all 24 real skills and agents (a
  dev-only probe, not a test dependency). A double-quoted description no longer shows its `\"`.
- **Choose rows:** the frontmatter `name:` (folder/file name fallback; the agent now reads
  `ai-kit-judge`, not `ai-kit-judge.md`) with the description, markup-escaped; when the name is
  not the folder/file name, `(folder)` follows dimmed, since that is what gets linked
  (`WizardContext.component_titles`). `PI_SKILLS` unchanged.
- **Empty descriptions, root cause:** three skills had a plain `description:` holding `: `, which
  strict YAML rejects, so a host's parser dropped the description: ai-kit-project-rules-agents,
  -cicd, -docker. Their frontmatter now holds the same text as a one-line `>-` block (frontmatter
  only; needs a skill-judge pass). The other skills named as empty (project-rules-all/-arch/
  -makefile/-precommit, gsd-curated-config, cst-refactor, markdown-to-pdf) parse as valid YAML with
  a description, and so do unrelated gsd-* skills that show empty in the same listing: inferred to
  be the host's skill-listing budget, not verified (the real `~/.claude` was not read).
- No SKILL.md lacks a description; no allowlist needed.

Verification: affected modules under uv OK; final `make test` exit 0 (unit 100/100, unit-uv 1/1,
integration 8/8, e2e 25/25, install 48/0, arch 1/1), `make pyright` exit 0, `make vulture` exit 0.
Snapshots `tmp/wizard-fixes/quick-data/task4-choose-{skills,agents,hooks}-40rows.txt`.
