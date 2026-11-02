# Phase 21: Ponytail code review

Scope: `git diff 782d477 HEAD -- . ':!.planning'` (36 files), plus the rendered runner
`.planning/scripts/cross-ai.mjs`. It was read against the callers of each changed function.
This review is read-only. Assumed load: one developer running the CLI on one machine.

## What this change does

Phase 21 adds the Cursor host. It adds a token-based `cursor-agent models` parser with a
captured fixture. It adds a PATH-scanning resolver for the guarded bare `agent` binary, written
twice: once in `detection.py` and once in the template-5 runner. It adds a `.cursor/gsd-core`
local root, two pinned Cursor subagents, and a `real_path` snapshot field. It extends the eval
harness for cursor: protected set, resolve-model-only chain, `--host-rewrite`.

Severity counts: **H 0, M 4, L 5.**

Checked and fine: `host.py` (one dict entry, two tests). The runner's absolute `which()` fix (the
`cwd-spawn` case proves grok's `agent` never runs). `_snapshot_report`/`_cmd_snapshot` exit codes
and the `snapshot ok` gate. `_generated_paths` for cursor. `routing._refresh_runtime`. The
SKILL.md/reference wording. The rendered runner equals the template body, apart from CONFIG.
Targeted suites pass: `test_ai_kit_spec_runtimes_table`, `test_cursor_agents`,
`test_ai_kit_spec_routing` (92 OK), and `test_ai_kit_spec -k Cursor/cursor/CrossAiTemplateText` (29 OK).

Not in this diff: the environ-matched reap code from 21-04. It lives only as evidence shell
in `.planning`, and the runner's `reapUnder` was not changed. The duplicated guarded-scan logic
between `detection.py` and the runner is necessary: the runner is a standalone file rendered into
target projects, so it cannot import Python. Each copy has its own grok-first test.

## Must fix

None.

## Should fix

### M1. The Python resolver caches a relative `./agent` path, so a later run can skip the cursor guard (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:185`, `routing.py:274-284`)

- **What this is:** `_guarded_hits` scans each PATH entry. For an empty entry (the cwd) it calls
  `which_fn(name, path=os.curdir)`. That returns the relative path `./agent`, and the tests pin
  this result (`tests/test_ai_kit_spec_runtimes_table.py:305,317`).
- **Problem:** The snapshot stores this relative `path` in the user-wide cache. Later, from
  another directory, `routing._refresh_runtime` can fail to re-resolve. It then falls back to
  `before.get("path")` (`routing.py:278`) and runs `./agent models` in the *new* cwd. That file
  never passed the `cursor-agent` basename check. The runner already fixed this for itself with
  `path.resolve` (template 5), so the two sides now disagree.
- **Fix:** Yield `os.path.abspath(hit)` in `_guarded_hits` (one call), and change the two test
  expectations to `os.path.join(cwd_dir, "agent")` (realpath'd). Nothing else moves.
- **If we skip it:** A user with an empty PATH segment can get a non-Cursor `agent` run as
  Cursor's model lister from whatever directory they are in.

### M2. A reflection shim in runtime code exists only to keep old test fakes working (`detection.py:4,169-187`)

- **What this is:** Before scanning, `_guarded_hits` uses `inspect.signature` to check whether
  `which_fn` accepts `path=`. If it does not, the scan is skipped without any warning.
- **Problem:** Production always passes `shutil.which`. The check only serves the roughly 30
  single-argument fakes in `tests/test_ai_kit_spec.py` (for example `:1157`, `:2014`, `:2706`). Any
  future wrapper written to the declared types `Callable[[str], str | None]` (`cli.py:121`,
  `runner_dispatch.py:210`) would silently lose the D-09 scan, and the bug D-09 fixed would come
  back with no test failing. The repo already has the plain convention in `gsd_tools.py:105,111`:
  `Callable[..., str | None]`, then call `which_fn(name, path=...)`. The extra leading
  `which_fn(name)` hit is the same as the scan's first hit, so it is also redundant.
- **Fix:** Delete the `inspect` block and the `first` pre-hit. Loop over the PATH entries and
  call `which_fn(name, path=d or os.curdir)`. Widen the two `Callable` hints to `[...]`. Give the
  remaining single-argument test fakes `**_kwargs`, as 21-01 already did for about 15 of them.
  About -10 runtime lines, and `import inspect` goes.
- **If we skip it:** This is a test-compatibility hack in stdlib runtime code, and a silent way
  for the guard fix to regress.

### M3. The ANSI and non-ASCII parser tests contain no ANSI or non-ASCII characters (`tests/test_ai_kit_spec.py:1554,1556,1570`)

- **What this is:** These tests prove that `parse_cursor_models` strips ANSI escapes and rejects
  non-ASCII id tokens (SPEC R4, 21-01 plan).
- **Problem:** The literals are `"m\\u00f6del"` and `"\\x1b[2m..."`. With the doubled backslash,
  each is a literal backslash, not `ö` or ESC. So `_ANSI_RE` never matches anything in the test.
  The ANSI test still passes because the mangled header just counts as "unrecognized" while
  `auto` is parsed. Delete the ANSI strip and both tests stay green. (Checked: the real ESC and
  `ö` inputs do behave correctly today.) The plan's own `<automated>` check used the real
  characters. The committed tests do not.
- **Fix:** Use single backslashes (`"mödel"`, `"\x1b[2m"`). Add one header-only ANSI case
  that must return `[]`; without stripping it would return `None`.
- **If we skip it:** Both SPEC R4 encoding rules have no test that can fail.

### M4. The "no grok in the runner" guard is switched off for 42% of the runner (`tests/test_ai_kit_spec.py:11641-11643`)

- **What this is:** `TestCrossAiTemplateText` checks that the runner never mentions `grok`
  outside its `scrubEnv` list.
- **Problem:** The three new self-test cases name their fake directories and marker `grok`. To
  make room, the test cuts out the whole `const cases = [` … `const only =` region: lines
  1540-2828 of a 3051-line file. Any future `grok` routing slipped into those self-tests now
  passes the guard. The fake binary is already called `other-agent-...`, so the word is not
  needed.
- **Fix:** Rename `grok` to `other` in the three cases (`cross-ai.mjs:2582-2661`: case names,
  `bin-agent-grok-*` directories, the `grok-ran` marker), then delete the 4-line carve-out.
- **If we skip it:** The invariant still has a name but checks less than half the file.

## Nice to have

### L1. The same strict entry is written twice (`tests/gsd_curated_eval.py:212` and `:308,314`)

`_strict_files` already maps `<home>/.cursor/hooks.json` to `_file_sha`. `snapshot()` then
writes the same label again with the same value. Fix: delete `cursor = ...` (`:308`) and the
second assignment (`:314`). -2 lines.

### L2. The `--host-rewrite` argparse block is copied on both subparsers (`tests/gsd_curated_eval.py:4949-4957`, `:5009-5017`)

The flag is needed: the pending interactive gate rewrites cursor's `cli-config.json`, and only
that label is exempted. But the 9-line `add_argument` block appears twice, word for word.
Fix: `for p in (snap, smoke): p.add_argument(...)` once. -8 lines. The `append` plus a
one-value `choices` is a generic list for a single label. A `store_true` would be shorter, but
it follows the `--scratch-root` style, so that part is fine.

### L3. The three new runner self-test cases repeat one setup, and one check has a dead branch (`skills/ai-kit-spec-review/references/cross-ai.mjs:2581-2664`)

Each case builds the same thing by hand: directory, `other-agent` script, node/git symlinks,
`agent` link (about 10 lines each). The `cwd` case's check still accepts `'\t./agent\t'`
(`:2633`), which `path.resolve` now makes impossible. The `cwd-spawn` case already proves the
real property, which is that the right binary runs. Fix: one `otherAgentFirst(c, dir, script)`
setup helper, drop the `./agent` alternative, and drop the print-argv `cwd` case or fold it
into `cwd-spawn`. About -25 lines.

### L4. `real_path` is written but never read (`detection.py:1045`, `routing.py:284`)

No code reads `real_path`. It is a D-09 decision ("informational only"), so it is kept. It
still costs a `realpath` per CLI, plus 8 test-equality edits. Fix if wanted: drop it, or name a
reader (doctor output). Otherwise leave it as a recorded decision.

### L5. The runner's `which` and `pathHits` duplicate one loop (`cross-ai.mjs:404-419`)

The bare-name branch of `which` equals the first value of `pathHits`. Fix:
`return pathHits(bin, envPath).next().value ?? null` after the slash check. -4 lines.

## Verdict

Verdict: fix M1 and M3 first. M2 and M4 are cheap cleanups worth folding into the same commit.
Lean: about -50 lines possible (M2 -10, L1 -2, L2 -8, L3 -25, L5 -4).
Not checked: `make test` in full and the e2e tier (only the targeted unit suites above were
run); the live Cursor behaviour (no live CLI probes, by rule).
