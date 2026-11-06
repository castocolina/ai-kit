---
phase: 31-removals-and-small-defects
plan: 03
subsystem: installer
tags: [installer, setup.py, install.sh, headless, pi, symlinks, path-resolution, prune]
requires: []
provides:
  - Alias-safe comparison of kit and home paths in tools/setup.py (parent resolved, leaf kept, component compare)
  - Checkout default for the kit dir (a checkout run links its own checkout)
  - Headless install and reconfigure prune of dead ai-kit links in the claude and pi skills roots
affects: [tools/setup.py, tools/install.sh, tests/test_setup.py, tests/test_install.sh]
tech-stack:
  added: []
  patterns: [os.path.commonpath component compare, pwd -P resolution in the bootstrapper]
key-files:
  created: []
  modified:
    - tools/setup.py
    - tools/install.sh
    - tests/test_setup.py
    - tests/test_install.sh
decisions:
  - "_is_inside resolves the parent of the path and keeps its leaf, so a kit entry that is itself a symlink is not followed out of the kit (review A11)."
  - "installed_links keeps the raw readlink target as its stored value; only the inside check joins the target with the link's directory."
  - "resolve_paths: AI_KIT_DIR, else the checkout holding the running setup.py. XDG_DATA_HOME no longer moves the kit (it still locates the bootstrap clone in install.sh)."
  - "Empty or unset HOME: setup.py returns 2 and install.sh exits 1, both with the same message, before any path is resolved and before the real-home refusal."
  - "Headless prune runs before linking in cmd_install_headless, with counts created first (review H3). Wizard prune is unchanged and still asks."
metrics:
  duration: "about 25 minutes (16:40-17:05 UTC)"
  completed: "2026-11-06"
  tasks: 3
  commits: 3
status: complete
commits: 3
plan_head_before: a9747a44ec66df8b86ca9f5e6bd8fcaa2ebe974b
plan_head_after: e638c54fc7faaa403df4167894f637df1c335200
actuals:
  tokens: 7790
  tasks: 3
  commits: 3
---

# Phase 31 Plan 03: Resolved kit paths, checkout default, headless dead-link prune Summary

Installer compares resolved paths so any alias spelling of the kit or home keeps ai-kit's own links (pi gets its three skills), a checkout run links its own checkout, empty HOME fails first with its own message, and headless install and reconfigure remove dead ai-kit links with one warning each.

## Performance

- Tasks: 3 of 3 complete, each committed as one logical commit with hooks on.
- Module timing (`tests.test_setup`): 3.2 s before Task 1, 4.4 s after Task 3 (under the 5 s threshold, so the subprocess classes stayed in `tests/test_setup.py`).

## Accomplishments

- `_is_inside` resolves the parent and the root and compares by path components; a relative link target is joined with its link's directory at every `os.readlink` inside-check (`installed_links`, `link_one`, `predecessor_candidates`, and the two hook-link callers).
- Alias re-install red check, pre-fix code: 23 "points outside ai-kit" warnings on the second run. After Task 1 the same scenario gives 0 foreign warnings and links `ai-kit-cross-ai`, `ai-kit-session-wake` and `jev-fast-decision` into the pi skills root.
- `resolve_paths` defaults `install_dir` to the checkout holding `tools/setup.py`; `install.sh` exports `INSTALL_DIR` resolved with `pwd -P`.
- Empty or unset HOME: `setup.py` prints `error: HOME is unset or empty; set HOME to your home directory` and returns 2 before the real-home refusal; `install.sh` exits 1 with the same message before `$HOME` expands.
- `_prune_headless` and `_headless_prune_roots`: `install --headless` (bare and with `--skills`) and `reconfigure --headless` remove dead ai-kit links under the claude root, then the pi root when it exists (`skills/` items only), one `warn: removing dead ai-kit link <cat>/<name> (entry removed upstream)` per link, sorted. `counts` is created before the prune.
- A link that vanishes between detection and `os.remove` counts as gone (`unlink_one` suppresses `FileNotFoundError`).
- Docstring, pi-root comment and `--headless` help text now say a bare run prunes dead ai-kit links. The README lines are plan 05's.

## Task Commits

1. **Task 1: alias spellings keep ai-kit's own links** - `8c63344` (fix): `_is_inside` rewrite, relative-target join at the readlink callers, `TestIsInsidePathComponents`, `TestResolvedKitPaths`.
2. **Task 2: checkout run and empty HOME** - `8f1f0a0` (fix): `resolve_paths` checkout default, HOME guard in `main`, `install.sh` HOME guard and `pwd -P` export, `TestCheckoutRun`, two `tests/test_install.sh` cases, rewritten `TestResolvePaths` expectations.
3. **Task 3: headless dead-link prune** - `e638c54` (fix): `_prune_headless`, `_headless_prune_roots`, prune call and hoisted `counts` in `cmd_install_headless`, reworded docs, `unlink_one` race handling, `TestHeadlessPrune`.

Task 3 first attempt failed the ruff hook (SIM105 on the new `try`/`except` in `unlink_one`). The fix (`contextlib.suppress`) was staged and the same commit re-run with hooks on. No `--no-verify`.

## Files Created/Modified

- `tools/setup.py` - `_is_inside`, `installed_links`, `link_one`, `predecessor_candidates`, hook-link inside-checks, `unlink_one`, `_prune_headless`, `prune_stale`, `_headless_prune_roots`, `resolve_paths`, `main` HOME guard, `cmd_install_headless` (prune, counts, docs), `--headless` help, module docstring.
- `tools/install.sh` - HOME guard before the `INSTALL_DIR` default, `pwd -P` resolution before the export.
- `tests/test_setup.py` - `TestIsInsidePathComponents`, `TestResolvedKitPaths`, `TestCheckoutRun`, `TestHeadlessPrune`; `TestResolvePaths` defaults rewritten to the checkout default.
- `tests/test_install.sh` - alias export case and empty-HOME case (section 1c and 1d).

## Decisions Made

See the `decisions:` list in the frontmatter. Each follows the plan text; none was a new choice beyond the plan.

## Deviations from Plan

### Notes (not deviations from the plan's requirements)

**1. Line numbers had drifted from the plan.** Anchors were located by content (for example `_is_inside` sat at 1187, not ~1076). This is the expected 30.1/30.2 drift from the brief.

**2. Interactive `prune_stale` path reorganised.** `apply_stale_prune` now runs inside the accepted-prompt branch and the headless branch calls `_prune_headless`, which applies too. Observable behaviour is unchanged: a declined prompt still returns the offered list without removing anything.

**3. Tests for `resolve_paths` defaults rewritten (planned in Task 2).** `test_defaults` and `test_xdg_data_home_without_ai_kit_dir` now expect the checkout default.

**4. No `tests/test_setup_install_e2e.py`.** The tier rule (A13) only moves the subprocess classes if the module grows by more than 5 s; it grew by 1.2 s.

**5. `scope.py` written from the prose section.** The plan's "Start snapshot and close check" section is prose, so `tmp/p31/03/scope.py` is an implementation of it with the `ai-kit-p31-` prefix. `selftest` printed `selftest ok` at start.

**6. Scratch `tmp/` contents.** `tmp/p31/03/` holds `scope.py`, `base_sha`, `run_id`, `start-*.json`, `time-before.txt`, `time-after.txt`, `red_check.py`, `summary_facts.py`. All are under the gitignored `tmp/`. The red-check scratch under `tmp/p31/03/red` was removed by the script.

No Rule 1-3 auto-fixes beyond the ruff SIM105 fix described above. No authentication gates. No checkpoints.

## Issues Encountered

- The Task 3 commit attempt failed the ruff hook (SIM105). Fixed before commit as described above.

## jev Calls

None. The plan fixed every decision point (headless prune order, the pi filter, the two HOME guards, the warning text). No 2-4 option choice was left open, so no `jev-fast-decision` request was made.

## User Setup Required

None. No external service or secret.

## Known Stubs

None.

## Threat Flags

None. The changes stay inside the T-31-06..09 mitigations in the plan's threat register: removal only of links whose resolved target is inside the kit and no longer exists (`stale_link_candidates`), component-compare `_is_inside`, HOME guard before any resolution, `FileNotFoundError` counted as gone.

## Self-Check: PASSED

Checks run after the last commit:

- Commits present in HEAD ancestry (`git merge-base --is-ancestor`): `8c63344`, `8f1f0a0`, `e638c54` - FOUND.
- No new files were created by this plan in the repository; the copied `.claude/gsd-core` and `.claude/scripts` are gitignored and never staged.
- `AI_KIT_REFUSE_REAL_HOME=1 make pyright` - passed.
- `tests/test_setup` - ok (466 tests); `tests/test_install.sh` - 48 passed, 0 failed; `shellcheck tools/install.sh tests/test_install.sh` - clean.
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p31/03/scope.py test` (`make test`) - exit 0. Tiers: unit 97/97 modules, integration 8/8, e2e 25/25 (includes `tests/test_install.sh`, 48 passed), arch 1/1.
- `scope.py close` after the last commit - last line `clean`.

## Orchestrator Steps

- orchestrator step: ship check per AGENTS.md (after the phase, not run by the executor). From the repository root: `AI_KIT_REFUSE_REAL_HOME=1 HOME=<a fresh scratch dir> python3 tools/setup.py install --headless --skills all --dry-run` (installer dry run in a scratch HOME; record the exit code).
- orchestrator step: on the unit branch tip in the main checkout, `python3 tools/setup.py install --headless --skills all`, then confirm that the pi skills root (`<pi agent dir>/skills`) links `ai-kit-cross-ai`, `ai-kit-session-wake` and `jev-fast-decision` into the kit, and that the pi loader sees them. Record the result in `31-VERIFICATION.md`.
- orchestrator step: R8 note for the phase record: `check`, `doctor` and `uninstall` run from a checkout now target that checkout (no `AI_KIT_DIR` needed).
