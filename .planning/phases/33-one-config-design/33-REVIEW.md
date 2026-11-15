---
phase: 33-one-config-design
reviewed: 2026-11-15T16:00:00Z
depth: standard
iteration: 2
scope: "git diff 66a3bfc..HEAD (the review-fix commits bf75b05..e5f0665 plus 7c2eeb2)"
files_reviewed: 16
files_reviewed_list:
  - skills/ai-kit-spec-review/ai_kit_spec/cli.py
  - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
  - skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py
  - skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py
  - skills/ai-kit-spec-review/ai_kit_spec/trust.py
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - .planning/scripts/cross-ai.mjs
  - skills/jev-fast-decision/scripts/jev_review.py
  - skills/ai-kit-cross-ai/references/subprocess-quota-policy.md
  - docs/config/design.md
  - README.md
  - tests/test_config_layers.py
  - tests/test_config_migrate.py
  - tests/test_jev_fast_decision.py
  - tests/test_toml_splice.py
  - tests/fixtures/cross_ai_selftest_secs.json
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 33: Code Review Report (iteration 2, re-review of the fixes)

**Reviewed:** 2026-11-15
**Depth:** standard (fix verification, with probes)
**Files Reviewed:** 16
**Status:** issues_found

## Summary

This pass reviewed only the fix commits in `66a3bfc..HEAD`. Both critical findings are fixed at the root
and have regression tests that would fail without the fix. That holds for CR-01 on the attack it names
(a project `config.toml` or old roster that is a link), and for CR-51 and SEC-W1. WR-01, WR-03, WR-04,
WR-52, WR-53, IN-05 and IN-06 are also fixed and tested. The probes ran with a temp HOME and temp
projects only: `tmp/auto/r325/c33-rr-py.py`, `c33-rr-splice.py` and `c33-rr-parse.mjs`. The runner
self-test cases for every fix pass (`self-test ok`). The template and `.planning/scripts/cross-ai.mjs`
differ only in the header stamp and the `<config>` block.

No fix opened a new security hole. The CR-01 guard does not block legitimate setups: a symlinked user
config folder, a project reached through a symlinked checkout path, and an absent `.aikit/` all still
work (probes E, F, G). Five warnings remain:
- Two original findings are only partly fixed. WR-02 still misplaces section comments when entries are
  reordered. WR-51 still refuses a valid multi-line nested array, and the new design.md sentence about
  it is wrong.
- `trust-local` now refuses any linked project `config.toml`, even when no migration is pending (dead end).
- `render-toml` still writes the user file through a `.aikit` folder link (the Python half of SEC-W1).
- The fixes' own line insertions made the design.md cites stale.

Necessity was not assessed in this fix-only pass (`necessity:` omitted).

## Original findings verified fixed

- CR-01: fixed in bf75b05. `cfg_confine_project_file` (`config_io.py:466-480`) refuses a linked project `config.toml` or old roster, or one that resolves outside `.aikit/` or onto the user config, before any migration or `render-toml` write. `TestProjectConfigLink` fails without it. Probe: the user file is untouched. Residuals: WR-101 and WR-102.
- CR-51: fixed in d5320bc. A root-level `runner.` or `runner =` key (bare, `"runner"` or `'runner'`) is refused (`cross-ai.mjs:3325`), so `holds` refuses too and nothing is appended. Covered by the `pure-toml-subset-refusals` rows and `retry-migrate-root-runner-key`. Residual: IN-101.
- WR-01: fixed in 5200bcb. A `default=` encoder handles dates and times. A pinned digest proves that date-free trust records stay valid. Residual: IN-103.
- WR-03: fixed in f7fbb2c. Trust is recorded for the `canonical` that was shown (`cli.py:914-919`). `TestTrustLocalOneRead` swaps the file after the one read and fails on the old code.
- WR-04: fixed in 54df2b6. `_published_intact` compares only `[lanes]` (`config_migrate.py:314-320`). The rename and trust carry still need the published lanes, so the check is not weakened. The new `TestConcurrency` case fails on the old code.
- WR-52: fixed in 6a70b69. `splitRetryEntries` migrates key by key and names each refused key with its value. Every value that the old runner's `validateRetryKey` accepted (finite numbers, integer arrays) is one `tomlValueText` can hold, so a refused entry loses nothing usable. Covered by `retry-migrate-odd-key`.
- WR-53: fixed in 85bdd78. `if (!o.printArgv) migrateRetrySources(...)`. `print-argv-no-migration` checks the GSD file, the user `cross-ai.json`, the user dir and `.aikit` byte for byte.
- SEC-W1: fixed in 6a70b69 (runner side). `aikitFolderUnsafe` refuses the project migration when `.aikit` is a link or resolves to the user config folder. `retry-migrate-aikit-link` would write the user `config.toml` without it. The Python side is not fixed: see WR-102.
- IN-05: fixed in 8649cb7. `consent` with no absolute home returns `no_user_config_dir` and exit 2, with no traceback (tested for grant, revoke and show).
- IN-06: fixed in 8649cb7. The legacy refusal and the migration run only for a `config.toml` target. The `[lanes]` `--replace` guard stays for every name. Tested.
- IN-53 (README and the `3019-3028` cite): fixed in e5f0665. The rest of the same paragraph is now stale: see WR-103.

## Warnings

### WR-02 (still open): reordering entries still moves a section comment, and the "directly above" case is untested

**File:** `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py:708-709`, `756-771`
**Issue:** 916d4a0 fixes the keep-order path (`_append_before_trailer`, the `kept` trailers) but not the
reorder path. `_assemble(blocks, plan.groups, _reorder(...), {}, {})` passes no trailers, so a reordered
group still carries its closing section comment with it. In the probe (`c33-rr-splice.py`, same output
before and after the fix), `set_array(SECTIONED, REVIEW, [{"key": "b"}, {"key": "a"}])` gives:
```
[[lanes.review]]
key = "b"

# ---- runner settings ----

[[lanes.review]]
key = "a"

[runner]
```
The `# ---- runner settings ----` comment now heads a review lane, which is WR-02's second effect. Also,
`test_remove_table_keeps_a_file_comment_separated_by_a_blank_line` already passes on 66a3bfc, so it is
not a regression test. The original third case, a file comment directly above `[lanes.policy]`, is
still deleted (probe: old and new give the same output). That may be the intended rule ("a comment
directly above a header is that header's lead"), but neither the fix report nor a test says so.
**Fix:** In the reorder path, split each moved group's lines with `_trailer_start`, move only the body,
and leave the trailer at the old group's position:
```python
if not _keeps_order(plan.pairs):
    kept = {i: _trailer(blocks[m[-1]].lines) for i, m in enumerate(plan.groups)}
    trimmed = {i: lines[: len(lines) - len(kept[i])] if kept[i] else lines
               for i, lines in _reorder(plan, results, rendered).items()}
    return _assemble(blocks, plan.groups, trimmed, {}, kept)
```
(Adapt this to `_reorder`'s result shape.) Add a reorder test on `SECTIONED`. For remove_table, either
record the lead rule in the docstring and in a test that asserts the deletion, or keep a lead comment
that is the first line of the file.

### WR-51 (partly open): a valid multi-line nested array still makes the runner skip the file, and design.md now misstates the rule

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:3295-3300`; `docs/config/design.md:57-61`
**Issue:** The fix report says "a nested array stays refused". That is not what the code does. The probe
(`c33-rr-parse.mjs`) shows the result depends on formatting:
- `[lanes.policy]` with `pairs = [\n ["a","b"],\n ["c","d"]\n]` gives `line 4: unsupported table name`,
  because the last element line matches `TOML_TABLE_HEADER_RE`.
- The same array with a trailing comma, or written on one line, is accepted, since opaque lines are
  skipped.

So the refusal is an accident of the header regex, and the notice it gives is misleading. Separately,
the new design.md sentence says the runner skips the whole file "for an inline table, a date, a nested
array, a multi-line string (except inside `[lanes]`...)". The code and `subprocess-quota-policy.md` do
not do that: an inline table or a date in `[models]` is accepted and skipped unread (probe:
`{"obj":{"runner":{"retry":{"base_s":2}}}}`). design.md and the policy doc now disagree.
**Fix:**
- In opaque context (`table === null`, not inside a runner table), treat a header-shaped line whose
  name `splitTomlName` cannot read as an opaque line instead of an error, the same as the trailing-comma
  form. A real header with an unreadable name could hide a runner table only if it named `runner`, and
  `splitTomlName` returns null for it either way. If D-07's "unsupported table name" refusal must stay,
  refuse only when the bracket text contains `runner`.
- Rewrite design.md:57-61 to match the policy doc: inside `[runner]`/`[runner.retry*]`, anything outside
  the subset skips the file. Anywhere in the file, an unreadable header name, a multi-line string
  outside `[lanes]`, an array of tables outside `[lanes]` or invalid UTF-8 also skips it.
- Add a self-test row for the no-trailing-comma nested array.

### WR-101 (new): `trust-local` refuses every linked project config.toml, even with nothing to migrate, so the trust warning leads to a dead end

**File:** `skills/ai-kit-spec-review/ai_kit_spec/cli.py:896`
**Issue:** bf75b05 calls `cfg_confine_project_file(local_path, env)` unconditionally in
`_cmd_trust_local`. The guard's own docstring scopes it to read-modify-write, and trust-local writes
nothing through the link (the record goes to the trust store, keyed by realpath). `cfg_resolve` still
reads a linked project `config.toml`; `cfg_migrate_project` runs the guard only when an old roster is
pending. So with a legitimate in-repo link (`.aikit/config.toml -> ../shared/aikit.toml`) holding a
command lane, every roster read prints "ignoring untrusted project-local config ... trust it with
`trust-local`", and `trust-local` (and `--show`) exits 2 with "is a link". Probe D:
```
D resolve: ok   (warn: ignoring untrusted project-local config ...)
D trust-local --show: (2, ..., '.aikit/config.toml: is a link; the project config is not migrated or written through a link ...')
```
The command lanes in that file can never be trusted. Before this commit they could.
`test_trust_local_refuses_a_linked_project_config` also ships an old roster, so the migration guard
alone covers it. No test needs the extra call.
**Fix:** Drop the extra call at `cli.py:896`. `cfg_migrate_project` already runs the guard whenever a
migration would write. If refusing linked project files for trust is wanted, make `cfg_resolve` refuse
them the same way, so the warning never points to a command that refuses.

### WR-102 (new, residual of CR-01): `render-toml` writes the user config.toml through a `.aikit` folder link

**File:** `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:512-517` (`cfg_migrate_target`); `cli.py:808-821`
**Issue:** `cfg_migrate_target` chooses the layer by `realpath(dirname(path)) == realpath(cfg_config_base(env))`.
Suppose a repo ships `.aikit` as a link to `~/.config/ai-kit`. Then
`render-toml --out <repo>/.aikit/config.toml` (spec-config's default local write) counts as the user
layer: no guard runs, and `publish` writes the user file. Probe C: exit 0, and the user `config.toml`
gained the `[lanes]` the user meant for the project. The content is the user's own, so trust is not
bypassed. But the user's global roster changes silently, for every project. If the user already has
`[lanes]`, the `--replace` prompt names `./.aikit/config.toml`, so the user approves replacing what looks
like the local file and loses the global roster. The original CR-01 text names this variant ("turns a
'local' spec-config write into a write of the user file"). The runner side got `aikitFolderUnsafe`
(SEC-W1); the Python side did not.
**Fix:** Count a target as the user layer only when it is spelled as the user layer, or when its folder
is not a link:
```python
base = cfg_config_base(env)
folder = os.path.dirname(os.path.abspath(path))
in_user_dir = (folder == os.path.abspath(base)
               or (not os.path.islink(folder) and os.path.realpath(folder) == os.path.realpath(base)))
```
Then the project guard refuses the folder-link case (`real == realpath(cfg_global_path(env))`). Add a
`TestProjectConfigLink` case with `.aikit` linked to the user dir.

### WR-103 (new): the fixes' insertions made the design.md line cites stale, in the paragraph IN-53 just fixed

**File:** `docs/config/design.md:109, 145, 146, 154, 155, 192-194` (and `240`, to re-check)
**Issue:** cb8fee5 and 6a70b69 insert about 78 lines into `cross-ai.mjs` before the migration code. The
cites were correct at 66a3bfc and are wrong now:

| Name | Cited | Actual |
|---|---|---|
| `findJsonKeySpan` | 3606 | 3655 |
| `removeRetryBlock` | 3629 | 3678 |
| `writeFileAtomic` | 3533 | 3582 |
| `migrateRetrySources` | 3807 | 3885 |
| `aiKitConfigDir` | 3311-3316 | 3360-3365 |
| `loadOverlay` | 3318 | 3367 |
| `resolveRetry` | 3454 | 3503 |

Python cites drifted the same way: `cfg_migrate_target` is cited as `config_io.py:493` and is at 512,
and `_cmd_render_toml` is cited as `cli.py:797` and is at 798. e5f0665 edited line 190 of this paragraph
and left 192-194 wrong. AGENTS.md treats stale docs as a defect, and the design record is what later
phases cite.
**Fix:** Re-cite every `cross-ai.mjs:`, `config_io.py:` and `cli.py:` line number in design.md against
HEAD. Better, cite by function name only, or add a check to `tests/test_config_design_record.py` that
each cited line holds the named symbol.

## Info

### IN-101 (new): a root-level runner key spelled with a unicode escape is not refused

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:3325`
**Issue:** `"runner".retry.base_s = 9` is read by tomllib as `runner.retry.base_s`. The CR-51 regex
does not match it, so the parser returns `{"obj":{}}` (probe). It is the user's own file and the form is
contrived, but a later migration would again append a second `[runner.retry]`.
**Fix:** Before the first header, decode a leading quoted key with `scanBasicString` and compare the
decoded first segment with `runner`. Or refuse any root line whose first quoted key contains a
backslash.

### IN-102 (new): `upsertTomlKeys` does not know about the multi-line strings the reader now accepts in `[lanes]`

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:3756-3768`
**Issue:** After WR-51, a `[[lanes.*]]` multi-line string can contain a line `[runner.retry]`.
`upsertTomlKeys` scans raw lines, takes that fake header as the target and inserts `base_s = 5` inside
the string (probe). `holds` then rejects the result, so nothing is written (fail closed). Still, a
legacy GSD block next to such a file never migrates, and the notice just repeats `merge did not verify`.
**Fix:** Skip lines inside an open multi-line string when locating headers, reusing `tomlOpenDelimiter`.

### IN-103 (new): the WR-01 date encoding can collide with a literal two-string array

**File:** `skills/ai-kit-spec-review/ai_kit_spec/trust.py:117-121`
**Issue:** `added = 2026-01-01` and `added = ["date", "2026-01-01"]` produce the same canonical bytes, so
a trust record for one also accepts the other. The changed value is not a command, so this is not
exploitable today. It only matters if a non-command lane key is ever substituted into argv.
**Fix:** Optional. Document the collision in the docstring, or encode with a form that TOML-derived JSON
cannot produce, such as a key that is not a valid bare TOML key, like `{"\u0000toml": ...}`.

## Accepted or skipped (reason holds)

- IN-01: an inline comment on a changed key line is lost. Skipped because D-08 only promises comments outside changed lines.
- IN-02, IN-03, IN-04, IN-08, IN-09: skipped by the fix brief. All are Info and none is a correctness risk at HEAD.
- IN-07: D-11 is owner-locked. The residual is recorded in 33-SECURITY.md.
- IN-52: the scope key is derived twice. This needs more than a one-line change. Only `GSD_WORKSTREAM=.` triggers it.
- IN-54: the judged skill files under `skills/ai-kit-spec-config/` are frozen this phase.
- IN-51 (part): `5.0` is accepted for an integer key, and U+2028 inside `kv`. Both are the user's own file, with no exploit (the `__proto__` part is fixed).
- IN-53 (part): `upsertTomlKeys` drops a trailing comment on the `migrated_from` line. The design.md:145 claim "a splice changes only the lines it owns" is still not exact for that one line. Accepted as Info. The stale cites in that table row are now covered by WR-103.

---

_Reviewed: 2026-11-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2_

## Iteration 3 (fix pass; the --auto cap of three iterations is reached, no fourth re-review)

Applied by the close-out orchestrator on 2026-11-15:

- WR-101: fixed 61ada6a. `trust-local` no longer calls the CR-01 guard itself; the guard runs inside
  the migration, only when an old roster is pending, so a linked project config.toml with nothing to
  migrate is read and can be trusted. Test `test_trust_local_trusts_an_in_repo_link_with_nothing_to_migrate`.
- WR-102: fixed 61ada6a. `cfg_migrate_target` treats a `.aikit/config.toml` target as the project layer
  even when `.aikit` links to the user config folder, so the guard refuses it and the user file is not
  written. Test `test_render_toml_refuses_a_project_aikit_dir_linked_to_the_user_folder`.
- WR-51 (doc part): fixed e7bdca1. design.md states the reader's skip rule as the code applies it (inside
  the runner tables vs anywhere in the file). The remaining code part (a multi-line nested array element
  alone on its line skips the file) stays: D-07 (owner-locked) lists nested arrays as outside the subset.
- WR-103: fixed e7bdca1 plus the docs commit after it. 26 moved line cites in design.md refreshed against the definitions
  (`tmp/auto/r325/c33-cites.py` found no stale single-line cite afterwards).
- Still open, not fixed: WR-02 remainder (reordering lanes moves a section comment with its entry; a
  comment directly above `[lanes.policy]` goes with the table): comment placement only, no data or trust
  effect; IN-101, IN-102, IN-103 (Info, no exploit; IN-102's guard already refuses the write).

Gates after iteration 3 are recorded in the close-out report (make test, pyright, lint, check-dogfood).

