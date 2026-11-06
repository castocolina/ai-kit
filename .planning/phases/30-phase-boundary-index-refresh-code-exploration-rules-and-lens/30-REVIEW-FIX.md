---
phase: "30"
review: 30-REVIEW.md
status: all_fixed_or_dismissed
fixed: 10
dismissed: 4
---

# Phase 30 code review fixes

Triage: jev-fast-decision first (one batch, 6 items; WR-07 supported 0.79, the rest needs_fallback
and decided here), then each finding checked in the code. No critical or high findings; the
review grades warnings and info.

| Finding | Severity | Result | Fix or reason |
|---|---|---|---|
| WR-01 | warning | fixed | `flow_index.refresh` adds the `.graphifyignore` line before the builds; test checks the line is there when `graphify update .` runs |
| WR-02 | warning | fixed | `flow_boundary.unit_range` returns None (brief: range unknown) when either recorded commit is gone; test |
| WR-03 | warning | fixed | `--opt=value` split before scanning; pi grep events carry `path`/`glob`/`pattern` (pi field names assumed from Claude's, marked `shortcut:`); tests |
| WR-04 | warning | fixed | `_gsd_config` deleted; `_graphify_config` uses `_config` |
| WR-05 | warning | fixed | `global_rules.drift()` deleted (no caller) |
| WR-06 | warning | fixed | e2e asserts no job ended when git returned (fake calls sleep 1.5 s); wall bounds loosened to 3 s |
| WR-07 | warning | fixed | `.graphifyignore` and `info/exclude` read with `surrogateescape`; `start` turns a `ValueError` from the boundary into `boundary: skipped: value_error: ...`; test |
| WR-08 | warning (necessity) | dismissed | working one-entry seam, used by three test sites; no defect, and the rewrite touches two modules and their tests for no behavior change |
| IN-01 | info | fixed | R08 clause comment restated |
| IN-02 | info | fixed | `--next` brief names `fold_adapters.base_branch(top)`, not a literal `main` |
| IN-03 | info | dismissed | symlinked host files: the second write is skipped safely and the next install reports `already`; message wording only |
| IN-04 | info | dismissed as inferred | no reproduced failure (`git worktree add` exports no `GIT_DIR` to post-checkout, checked by the reviewer) |
| IN-05 | info | dismissed (accepted) | the line goes in once per project and only until it is committed; the foreground boundary prints the `commit it` note, and the open start-step medium in 30-JUDGE.md tracks the commit rule |
| IN-06 | info | fixed (spec regex) | `_SPEC_LINE` uses `[ \t]*`, so an empty `**Spec:**` line never captures the next line; the codegraph "lock" substring stays (wrong line text, harmless) |

Security gaps closed in the same pass (30-SECURITY.md): T-30-06 (refresh leaves
`.planning/config.json` byte-identical), T-30-07 (advisor tokens appear in `RULE_CLAUSES[0]`).
