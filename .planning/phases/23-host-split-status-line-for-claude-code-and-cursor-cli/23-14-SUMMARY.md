---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 14
subsystem: infra
tags: [setup, status-line, cursor, claude, headless, atomic-write]

# Dependency graph
requires:
  - phase: 23-08
    provides: the shared exact-argv command-ownership parser and migrate_statusline
  - phase: 23-13
    provides: tools/cursor-status-line.py (the entry the Cursor statusLine command runs)
  - phase: 23-15
    provides: statusline-doctor.py --host pointer referenced from the README
provides:
  - Paths.cursor_config_dir / cursor_cli_config / cursor_status_line / cursor_config_toml /
    cursor_sample, resolved only through config_doctor_checks.resolve_runtime_config_paths()
  - detect_statusline_cursor / wire_statusline_cursor / unwire_statusline_cursor on the
    unset-ours-foreign classification, the CLI's own statusLine schema and the atomic primitives
  - headless --with-statusline[=claude,cursor] with host selection validated at command entry,
    Claude wired before Cursor, and per-host uninstall
affects: [status-line, cursor, phase-23-16, phase-23-17, phase-23-18]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 26650
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cursor's config reads go through one comment-tolerant reader (_cursor_config_read) that
      reports json | jsonc | absent | bad; detection uses all four, the writer acts only on json"
    - "Write-ordered re-read compares the entry TEXT the caller classified, not just its class"

key-files:
  created: []
  modified:
    - tools/setup.py
    - tools/config_doctor_checks.py
    - tests/test_setup.py
    - README.md

key-decisions:
  - "D-21: `Paths.cursor_config_dir`/`cursor_cli_config` come from
    `config_doctor_checks.resolve_runtime_config_paths(env)` cursor key and nothing else; that
    resolver now treats a blank OR whitespace-only `CURSOR_CONFIG_DIR`/`XDG_CONFIG_HOME` as
    absent so the chain falls through. The hooks' `cursor_dir` keeps its older two-step rule
    (backlog 999.2) — the two are pinned by expected precedence, not by parity."
  - "Cursor ownership is decided by the shared exact-argv parser on all four paths (migration,
    detection, refresh, uninstall); a `.backup`/`.bak` suffix, an argument-only path, a `bash -c`
    wrapper and a `cd && ` chain all stay foreign."
  - "The re-read before the atomic replace aborts when the fresh entry text differs from the text
    the caller classified (so unset→foreign and ours→unreadable abort too), while re-seeing the
    exact foreign string a human just approved is not a change and proceeds."
  - "A `cli-config.json` carrying JSONC comments is classified by detection (read through the
    comments) but never rewritten by wire or unwire: ai-kit's writer emits plain JSON and would
    delete those comments. README documents this as a known gap rather than degrading silently."
  - "The Cursor status-line TOML is NOT copied by `install` in this plan (only its Paths fields
    exist); README says the line renders ai-kit defaults with no file and points at the sample,
    because the wizard that writes it is 23-16/23-17."

patterns-established:
  - "Host selection at command entry: unknown name = argparse usage error (2), valid-but-undetected
    = one message and exit 1, both before migration, backup, link, hook, example or config write —
    proven by a whole-scratch-tree snapshot, with a non-vacuity row showing a valid selection does
    move the tree."
  - "Per-host uninstall independence: each host's file is classified and rewritten on its own, so a
    foreign or unreadable Cursor config never blocks Claude's entry removal, or the reverse."

requirements-completed: [STL-05]

coverage:
  - id: D1
    description: "Paths gains the five Cursor fields from the one shared resolver, with the
      non-blank precedence chain and the hooks' cursor_dir left unchanged."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestCursorConfigPathResolver.test_shared_resolver_nonblank_precedence
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestCursorConfigPathResolver.test_paths_gains_the_five_cursor_fields
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestCursorConfigPathResolver.test_hooks_cursor_dir_is_unchanged_by_xdg
        status: pass
    human_judgment: false
  - id: D2
    description: "Headless --with-statusline=cursor against a scratch CURSOR_CONFIG_DIR writes
      cli-config.json with exactly {type, command} at 2-space indent, quotes the entry path when
      the install dir holds a space, never materializes an absent dir, creates the file in a dir
      that exists without one, and the wired command renders a line from the synthetic payload."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_detected_cursor_dir_gets_the_exact_two_key_entry
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_install_dir_with_space_quotes_the_entry_path
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_absent_cursor_dir_is_never_materialized
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_adjacency_existing_dir_without_config_file_is_detected
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_wired_command_renders_a_line_from_the_synthetic_payload
        status: pass
      - kind: other
        ref: "Task 1 verify: env -i scratch HOME setup.py install --headless --with-statusline=cursor"
        status: pass
    human_judgment: false
  - id: D3
    description: "One shared exact-argv ownership parser across migration, detection, refresh and
      uninstall: suffix and argument-only counterexamples stay foreign on both hosts."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineOwnershipCounterexamples.test_counterexamples_are_foreign_on_both_hosts
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineOwnershipCounterexamples.test_headless_refresh_refuses_and_leaves_both_files
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineOwnershipCounterexamples.test_uninstall_leaves_them_and_removes_the_real_entry
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineOwnershipCounterexamples.test_migration_leaves_a_legacy_named_counterexample_alone
        status: pass
    human_judgment: false
  - id: D4
    description: "The detect/wire matrix: 2 hosts x 3 states x 3 modes (18 subTests), unrelated
      keys preserving parsed values and order, ours-refresh changing only `command` and keeping
      padding/updateIntervalMs/timeoutMs, a new entry holding no non-default knob, bare-string and
      shell-type and every malformed sibling/unknown-key shape refused by the writer and detected
      foreign, dry runs writing nothing, foreign x headless exiting 1 byte-identical."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_matrix_two_hosts_three_states_three_modes
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_matrix_foreign_headless_exits_one_on_both_hosts
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_cursor_ours_refresh_changes_only_command
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_cursor_new_entry_writes_no_non_default_knob
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_cursor_invalid_shapes_refused_by_writer_and_foreign_by_detector
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_dry_run_writes_nothing_on_both_hosts
        status: pass
    human_judgment: false
  - id: D5
    description: "T-23-47 write ordering: a foreign entry, or a file that stopped parsing,
      appearing between the classified read and the atomic replace aborts the write (patched
      reader, reader called twice, file byte-identical)."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_writer_refuses_when_the_entry_changed_before_the_write
        status: pass
    human_judgment: false
  - id: D6
    description: "Headless host selection: bare wires every detected host Claude-first, the
      =claude,cursor form selects (order-normalized, de-duplicated, case/whitespace tolerant),
      unknown names exit 2 and undetected names exit 1 before ANY write — proven with a full
      scratch-tree snapshot combined with legacy migration and requested skill/hook/example
      writes, plus a non-vacuity row; no host detected prints nothing-to-wire and exits 0; a
      second run changes no byte."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostSelection.test_parse_statusline_hosts_selection_table
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostSelection.test_bare_form_wires_claude_before_cursor
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostSelection.test_second_headless_run_changes_no_byte
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostSelection.test_explicit_selection_wires_only_that_host
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineSelectionBeforeAnyWrite.test_invalid_or_undetected_host_snapshot_is_unchanged
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineSelectionBeforeAnyWrite.test_a_valid_selection_does_change_the_tree
        status: pass
      - kind: other
        ref: "scratch-HOME probes: --with-statusline=bogus -> 2, =cursor with no dir -> 1, bare twice -> 0 and no byte change, no dir materialized"
        status: pass
    human_judgment: false
  - id: D7
    description: "Per-host uninstall: ai-kit's entry removed from each host's file only when it is
      ours, foreign entry and the other host's file byte-identical, unparseable file skipped with a
      warning and exit 1, missing file never materialized, both TOMLs left in place, dry run writes
      nothing."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineUninstallPerHost.test_removes_ai_kit_entry_on_both_hosts_and_keeps_tomls
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineUninstallPerHost.test_each_host_is_independent
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineUninstallPerHost.test_unparseable_host_file_is_skipped_with_a_warning_and_exit_one
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineUninstallPerHost.test_missing_host_file_is_skipped_and_never_materialized
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineUninstallPerHost.test_wired_cursor_entry_survives_a_dry_run
        status: pass
    human_judgment: false
  - id: D8
    description: "T-23-48: a file that parses as neither JSON nor JSONC is never rewritten by wire
      (headless or interactive-yes) or by unwire, on either host; a JSONC-commented Cursor file is
      detected honestly and left byte-identical with the reason named."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_setup.py#TestStatuslineHostMatrix.test_unparseable_host_file_is_never_rewritten_by_wire
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_unparseable_cli_config_is_refused_and_left_byte_identical
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_jsonc_commented_config_is_never_rewritten
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_detection_reads_through_comments_but_the_writer_still_refuses
        status: pass
      - kind: unit
        ref: tests/test_setup.py#TestHeadlessCursorStatusline.test_unwire_refuses_a_commented_config_naming_the_reason
        status: pass
    human_judgment: false
  - id: D9
    description: "README: the bare flag now wires every detected host (Claude, then Cursor), the
      =claude,cursor form and its errors, a Cursor CLI status-line section (what it shows, the
      ≈-marked inferred quota, resolver precedence, the JSONC gap, per-host uninstall), the
      uninstall paragraph and the CURSOR_CONFIG_DIR env override."
    requirement: STL-05
    verification:
      - kind: other
        ref: "grep 'with-statusline=claude,cursor' README.md (Task 2 verify)"
        status: pass
      - kind: other
        ref: "make validate (all hooks, all files)"
        status: pass
    human_judgment: false
  - id: D10
    description: "Project-wide gates: make test (unit, unit-uv, integration, e2e incl.
      test_install.sh) and make validate (ruff, pylint, pyright, vulture, shellcheck, py-compile,
      core and wizard unittest hooks) exit 0; the working tree is clean."
    requirement: STL-05
    verification:
      - kind: other
        ref: make validate
        status: pass
      - kind: other
        ref: make e2e-test
        status: pass
      - kind: other
        ref: "uv run python tools/run_unittest_parallel.py --group e2e (11/11 modules)"
        status: pass
    human_judgment: false

# Metrics
duration: 50min
completed: 2026-10-24
status: complete
orchestrator_verify: "pending"
orchestrator_verify: "VERIFY 23-14: 2/2 passed"
---

# Plan 23-14: setup multi-host status line (STL-05, setup side) Summary

**`tools/setup.py` now detects, wires and unwires the status line on Claude and Cursor with the
same three-state classification and the same atomic primitives, selects hosts headless at command
entry, and never overwrites a foreign entry without a human yes.**

## Performance

- **Duration:** ~50 min for this continuation (Task 2 + summary); Task 1 landed in the plan's
  earlier run
- **Tasks:** 2
- **Files modified:** 4 (`tools/setup.py`, `tools/config_doctor_checks.py`, `tests/test_setup.py`,
  `README.md`)

## Accomplishments

- **D-21 shared resolver:** `Paths` gains `cursor_config_dir`, `cursor_cli_config`,
  `cursor_status_line`, `cursor_config_toml`, `cursor_sample`, all Cursor paths resolved through
  `config_doctor_checks.resolve_runtime_config_paths()` — the sole Cursor resolver, now treating a
  blank *or* whitespace-only override as absent so `CURSOR_CONFIG_DIR` → `$XDG_CONFIG_HOME/cursor`
  → `~/.cursor` falls through. The hooks' separate `cursor_dir` is untouched (backlog 999.2) and
  tests pin expected precedence rather than parity.
- **D-23 Cursor shape + writer:** `detect_statusline_cursor` / `wire_statusline_cursor` /
  `unwire_statusline_cursor` pin Cursor's own `statusLine` object (`type == "command"` + non-empty
  string `command`, only `padding`/`updateIntervalMs`/`timeoutMs` as optional siblings; bare
  strings, `{"type": "shell"}`, unknown keys, bools and non-positive timings are foreign/refused),
  refresh only `command` for an "ours" entry, write no non-default knob for a new one, run the
  command as `python3 -S <entry>` with `shlex.quote` when the path holds whitespace, skip when the
  parent dir is absent, and re-read + re-classify immediately before `_atomic_write_json`.
- **Headless host selection (SPEC R11):** `--with-statusline` is optional-valued; the bare form
  wires every detected host Claude-first, `=claude,cursor` selects, an unknown name is usage exit
  `2`, a valid-but-undetected name is exit `1`, and validation happens at command entry so no
  migration, backup, link, hook, example or config write can happen first — proven by a
  whole-scratch-tree snapshot table plus a non-vacuity row. Empty detection reports "nothing to
  wire" and exits 0; a second run changes no byte.
- **Per-host uninstall:** `cmd_uninstall` unwires each host independently through the shared
  atomic primitives, only for an entry that is ai-kit's own; foreign entries, the other host's
  file and both TOMLs stay byte-identical, and an unreadable file is skipped with a warning (exit
  1, unchanged semantics).
- **Tests:** 403 tests in `tests/test_setup.py` (364 at this plan's base) including the 18-row
  host x state x mode matrix, the ownership counterexamples on all four paths, malformed-shape and
  injected-race rows, per-host uninstall and the selection-before-any-write snapshot.
- **README:** new "Cursor CLI status line" section (what it renders, the `≈`/`≈*` inferred-quota
  wording with the `inferred — undocumented Cursor API` label, resolver precedence, the JSONC
  known gap, per-host uninstall, the doctor `--host cursor` pointer), the rewritten headless
  `--with-statusline` bullet and uninstall paragraph, and `CURSOR_CONFIG_DIR` in the env list.

## Task Commits

Each task was committed atomically:

1. **Task 1: Cursor wiring + headless host selection** - `a6f195c` (feat)
2. **Task 2: matrix tests, per-host uninstall, README** - `4fbe4a3` (feat)
3. **Plan summary** - this commit (docs)

## Files Created/Modified

- `tools/setup.py` — Cursor `Paths` fields, the Cursor statusLine schema guard,
  `_cursor_config_read`/`_cursor_config_for_write`, `detect_statusline_cursor`,
  `wire_statusline_cursor`, `_cursor_commit_statusline`, `unwire_statusline_cursor`,
  `statusline_hosts_detected`, `parse_statusline_hosts` + `UndetectedStatuslineHost`,
  `_headless_wire_statusline`, `main` entry validation, per-host `cmd_uninstall`
- `tools/config_doctor_checks.py` — `resolve_runtime_config_paths()` treats a blank or
  whitespace-only Cursor override as absent (D-21 non-blank precedence)
- `tests/test_setup.py` — `TestCursorConfigPathResolver`, `TestHeadlessCursorStatusline`,
  `TestStatuslineOwnershipCounterexamples`, `TestStatuslineHostMatrix`,
  `TestStatuslineUninstallPerHost`, `TestStatuslineHostSelection`,
  `TestStatuslineSelectionBeforeAnyWrite`, `_tree_snapshot` helper
- `README.md` — Cursor CLI status-line section, headless host-selection rewrite, per-host
  uninstall paragraph, `CURSOR_CONFIG_DIR`

## Decisions Made

- **`seen`-text re-read rule (superset of "became foreign").** The advisory jev ladder
  (`decide.py ladder`, laya local backend, advisory only) preferred the literal
  "abort only when the entry became foreign" wording (top 0.74). The evidence went the other way:
  that wording still overwrites in two real races — an entry the writer saw as *unset* that becomes
  foreign, and our command replaced by someone else's while the class stays the same — and it would
  also rewrite a file that stopped parsing. Comparing the entry text the caller classified (and, if
  foreign, showed the human) aborts every one of those while still letting an approved replacement
  of that exact string proceed, which satisfies the plan's wording as a subset. Pinned by
  `test_writer_refuses_when_the_entry_changed_before_the_write` (three rows, reader call count 2).
- **Comment-tolerant Cursor read, comment-refusing Cursor write.** The same ladder run returned
  `strict-read` as a low-confidence fallback (`top 0.56`, `decided_by: own_reasoning`), i.e. no real
  verdict. Detection reporting `unset` for a file that in fact holds a foreign `statusLine` would
  state less risk than there is, which AGENTS.md forbids ("no diagnostic or detection result is
  presented with more certainty than its actual sourcing"), so detection reads through comments.
  The write stays strict: ai-kit emits plain JSON and the phase explicitly does not build a
  byte-preserving JSON editor, so a JSONC file is refused with the reason named, byte-identical,
  exit 1 — documented in the README as a known gap rather than silently degraded.
- **No Cursor TOML copy in `install`.** D-21 only asks for the `Paths` fields; the writer that
  materializes `cursor-statusline.toml` is the 23-16/23-17 wizard, so the README was corrected to
  say the line renders ai-kit defaults with no file and the sample is a starter to copy (verified
  against `copy_recipe_if_absent`, which this plan leaves Claude-only).

## Deviations from Plan

- The Cursor host reads use `_cursor_config_read` rather than `_read_json_checked` directly (the
  tolerant-detection decision above). `_read_json_checked` still governs the Claude host and the
  hook files, and every write — both hosts — still goes through `_atomic_write_json`/
  `_read_json_checked`-class checks; `tests/test_setup.py` pins that an unparseable file is never
  rewritten by wire or unwire on either host.
- Task 2's work also carried one behavior change made in the earlier run of this plan that had been
  left uncommitted: the `seen`-text re-read rule. Both were tested and are covered above.

## Deleted tests

None.

## Pre-existing failures

None. `tests/test_setup.py` was green at this plan's base commit `ba0e40b` in a `git archive` copy
(364 tests, 1/1 modules passed) and is green at HEAD (403 tests, 1/1 modules passed).

## Gate Results

- `uv run ruff check tools skills tests` — pass
- `uv run pylint` (tools/setup.py, 10.00/10) — pass
- `uv run pyright` — 0 errors
- `uv run vulture` — clean
- `make test-unit`, `--group integration` (4/4 modules), `make e2e-test` (e2e group 11/11 modules,
  incl. `bash tests/test_install.sh` 45 passed / 0 failed), `make validate` (all hooks, all
  files) — pass
- Both plan `<verify><automated>` commands pass; the orchestrator-level scratch-HOME probes (wire
  both hosts, idempotent second run, `=bogus` → 2, `=cursor` without a dir → 1 with nothing
  materialized) were run manually and pass.

## Issues Encountered

- The earlier run of this plan timed out with Task 2's edits uncommitted; those edits were kept,
  reviewed, and one vacuous test among them was repaired rather than shipped: the injected-race
  test still patched `_read_json_checked` after the Cursor read had moved to
  `_cursor_config_read`, so it passed without exercising the re-read at all (an empty file was
  already "unparseable"). It now patches the reader the writer actually uses and asserts the reader
  ran twice.
- Owner-only rows are unaffected by this plan.

## User Setup Required

None — no external service configuration. On a machine with both `~/.claude` and a Cursor config
dir, `python3 tools/setup.py install --headless --with-statusline` wires Claude then Cursor.

## Next Phase Readiness

- 23-16/23-17 (wizard) can call `wire_statusline_cursor(..., tty, dry)` directly: the interactive
  yes/no for a foreign entry, the headless refusal, the adjacency guard and the re-read are all in
  place and tested; `statusline_hosts_detected`/`parse_statusline_hosts` give the host list.
- 23-15's doctor already reads `Paths.cursor_cli_config`; no interface changed under it.
- Cursor hooks stay on the separate `Paths.cursor_dir` rule (backlog 999.2).

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
