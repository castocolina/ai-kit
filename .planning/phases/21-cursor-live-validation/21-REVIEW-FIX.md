---
phase: 21-cursor-live-validation
fixed_at: 2026-10-19T05:20:50Z
review_path: .planning/phases/21-cursor-live-validation/21-REVIEW.md
iteration: 1
findings_in_scope: 16
fixed: 15
skipped: 1
status: partial
---

# Phase 21: Code Review Fix Report

**Fixed at:** 2026-10-19
**Source reviews:** `21-REVIEW.md` (CR-01, WR-01..06, IN-01..05) and `21-PONYTAIL-CODE-REVIEW.md`
(M1-M4, L1-L5). Overlaps count once: M1=WR-01, M2=WR-05, M3=WR-03, L1=IN-01, L5=IN-03.
**Iteration:** 1

**Summary:**
- Findings in scope: 16 (CR-01, WR-01..06, M4, IN-01..05, L2, L3, L4)
- Fixed: 15
- Skipped: 1 (L4)

## Fixed Issues

| ID | Commit | Change | Regression test |
|----|--------|--------|-----------------|
| CR-01 | ff851ff | Runner `parseCursorListingIds` ported to `parse_cursor_models` rules: ANSI strip, Python `splitlines()`/`strip()` sets, the ASCII id alphabet, nameless lines only after the header, `null` for unrecognized output. Template 6: `TEMPLATE_VERSION = 6`, header, 7 goldens, `template=N` pins, README/SKILL.md/runner.md/tooling_guidance version text. Tracked `.planning/scripts/cross-ai.mjs` re-rendered through `ensure-runner --cwd .` (`runner: change`); CONFIG block byte-identical to the pre-upgrade copy, `script_state` pristine, body equal to the template | `TestCursorParserParity` runs both parsers on `tests/fixtures/cursor_models*.txt` plus 13 edge cases (the CR-01 example, ANSI, CRLF, non-ASCII, `Loading...`, nameless with no header); self-test case `cursor-nameless-listing-preflight` (fails with the old parser: exit 69 `bad_model`) |
| WR-06 | a8e9185 | A bare or flagged token counts only after `Available models`; `Loading...`/`Error` now return None | `test_bare_token_without_header_is_unrecognized` |
| WR-03 / M3 | a8e9185 | Real ESC and U+00F6 literals; two added cases fail without the ANSI strip | `test_ansi_header_and_nameless_model`, `test_non_ascii_id_is_unrecognized_and_does_not_hide_valid_ids` |
| WR-05 / M2 | ca04e1c | `inspect.signature` check and the separate first hit removed; the scan always calls `which_fn(name, path=...)`. `path_env` threaded through `detect_installed_clis` and `build_runtimes_snapshot`. `which_fn` hints widened to `Callable[..., str \| None]`; single-argument test fakes now take `**_k`. Five tests that count calls dedupe them, because the guarded name is looked up once per PATH entry | `test_path_env_reaches_the_snapshot_scan` |
| WR-01 / M1 | 7138855 | `resolve_runtime_binary` returns `os.path.abspath(found)` for every hit | `test_trailing_empty_path_segment_is_the_cwd` and `test_empty_path_scans_the_cwd` expect the absolute path |
| WR-02 | 6c72b03 | New `detection.cached_binary_usable`: a cached path is reused only if it is absolute and, for a guarded name, still passes the realpath basename guard | `test_failed_lookup_drops_a_cached_agent_that_fails_the_guard` (an absolute non-cursor `agent` and a stale `./agent`; no listing runs) |
| WR-04 | 5c20cf5 | `<home>/.cursor/agents` and `skills` use `_tree_sha`. Reason: ai-kit's installer links agents and skills into these directories, so an overwritten file or a retargeted link is a real write. `21-INTERACTIVE-CURSOR.md` wording updated | `test_cursor_agents_skills_hooks_are_protected` now expects a content edit and a retargeted link to fail |
| M4 | ff851ff | The three D-09 self-test cases name their fakes `other` (not `grok`); the 4-line carve-out in `test_retired_cli_absent_outside_scrub_entry` is deleted | `test_retired_cli_absent_outside_scrub_entry` (whole file) |
| L3 | ff851ff | `otherAgentFirst`/`cwdCursorAgent` setup helpers shared by the three cases; the unreachable `./agent` branch is dropped. The print-argv `cwd` case is kept because it pins the absolute path | runner `--self-test` |
| IN-01 / L1 | 5c20cf5 | Duplicate `hooks.json` assignment and the `cursor` local removed | existing hooks assertion |
| IN-02 | 5c20cf5 | `CURSOR_CLI_CONFIG_LABEL` defined before `_strict_files`, which now uses it | `test_cursor_config_change_is_strict` |
| L2 | 5c20cf5 | `--host-rewrite` declared once, in a loop over the snapshot and smoke subparsers | existing `--host-rewrite` tests |
| IN-03 / L5 | ff851ff | `which()` returns `pathHits(...).next().value ?? null` | runner `--self-test` |
| IN-04 | 516ff63 | The bundle-parse test parses every `_agent_files()` entry and asserts each result is not None | `test_files_parse_with_the_bundle_rules` |
| IN-05 | ff851ff | runner.md says an empty PATH entry is the cwd, which lets a checkout supply its own `agent`, and advises against empty entries in untrusted checkouts | n/a (documentation) |

WR-06, WR-01, WR-02 and CR-01 change parser or resolver logic: **fixed: requires human
verification** (confirm the header rule and the absolute-path cache semantics match intent).

## Skipped Issues

### L4: `real_path` is written but never read

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py`, `routing.py`
**Reason:** This is a recorded D-09 decision ("informational only"). The ponytail review itself
says to keep it unless a reader is named. Not a defect.
**Original issue:** `real_path` costs one `realpath` per CLI, and no consumer reads it.

## Notes

- `skills/ai-kit-gsd-curated-config/SKILL.md` (line 196, `template 5` -> `template 6`) and
  `references/runner.md` (title, plus the IN-05 sentence) changed because the template bump
  requires it. Both are skill-judged, so the judge digest is re-keyed and the skill-judge loop
  must re-run before the phase closes.
- The fixes were made directly in the existing `gsd/v1.3-curated-config-v2` worktree, not a
  nested review-fix worktree, because that worktree has the uv venv the gates need. No temp
  branch or recovery sentinel was created.
- Several findings went into one commit where they shared a file or the single template
  bump. Each commit message lists the IDs it covers.

## Verification

All gates ran in this worktree (`.claude/worktrees/v13-curated-config-v2`) at 516ff63:

- `make validate`: ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest (core) and
  unittest (wizard, uv) all passed.
- `python3 tools/run_unittest_parallel.py --group unit`: 43/43 modules passed, 4150 tests.
- `uv run python -m unittest tests.test_cross_ai_runner_e2e`: 13 tests OK, including the full
  template `--self-test` with the new and renamed cases.
- The new self-test case fails against the old parser. A tmp copy of the template with the old
  function prints `self-test FAIL cursor-nameless-listing-preflight: exit 69 expected 0`.
- No live AI CLI was run.

---

_Fixed: 2026-10-19T05:20:50Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
