# Deferred Items — Phase 6

## `make validate` pre-existing ruff/pylint failures (out of scope for 06-02)

`make validate` (the `pre-commit run --all-files` gate) fails on `ruff` and
`pylint` hooks, but every failing line is in files Plan 06-02 never touched:

- `tools/status-line.py` (multiple `E501` line-too-long, one `R0914`
  too-many-locals in pylint)
- `tools/wizard_app.py` (`RUF012` mutable class-attribute default, one
  `E501`)
- `tests/test_ai_kit_spec_superpowers.py` (`RUF059` unused unpacked
  variable, two `E501`)

These files were last touched by unrelated commits (`b80a26a`
"feat(08-01): add burn-rate ratio helpers...", `b9c14aa`
"feat(ai-kit-spec): add model-discovery/curation...", `8ae1821`
"fix(ai-kit-spec-execute-superpowers): ..."), none of which belong to
Phase 6. `git status --short` for this plan's work shows only:

```
 M skills/ai-kit-agents-md-checker/SKILL.md
 M skills/ai-kit-agents-md-checker/ai_kit_agents_md_checker/cli.py
 M tests/test_ai_kit_agents_md_checker.py
?? skills/ai-kit-agents-md-checker/ai_kit_agents_md_checker/remediation.py
```

`uv run ruff check` against exactly those four paths returns a clean `[]`.
`pylint`/`pyright`/`vulture`/`shellcheck`/`py-compile`/both `unittest` hooks
all pass. Per the executor's Scope Boundary rule ("only auto-fix issues
directly caused by the current task's changes"), these three unrelated
files are NOT fixed here — logged for a future cleanup pass instead.
