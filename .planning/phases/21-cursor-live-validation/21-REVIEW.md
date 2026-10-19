---
phase: 21-cursor-live-validation
reviewed: 2026-10-19T00:00:00Z
depth: deep
files_reviewed: 37
files_reviewed_list:
  - .pre-commit-config.yaml
  - Makefile
  - README.md
  - cursor-agents/composer-worker.md
  - cursor-agents/grok-worker.md
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py
  - skills/ai-kit-gsd-curated-config/references/runner.md
  - skills/ai-kit-gsd-curated-config/references/v1-path.md
  - skills/ai-kit-spec-review/ai_kit_spec/detection.py
  - skills/ai-kit-spec-review/ai_kit_spec/routing.py
  - skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - .planning/scripts/cross-ai.mjs
  - tests/fixtures/curated_config_v2/golden/claude-mvp-adaptive.json
  - tests/fixtures/curated_config_v2/golden/claude-rigorous-adaptive.json
  - tests/fixtures/curated_config_v2/golden/claude-standard-adaptive.json
  - tests/fixtures/curated_config_v2/golden/codex-mvp-adaptive.json
  - tests/fixtures/curated_config_v2/golden/codex-mvp-budget.json
  - tests/fixtures/curated_config_v2/golden/codex-rigorous-adaptive.json
  - tests/fixtures/curated_config_v2/golden/codex-standard-adaptive.json
  - tests/fixtures/cursor_models.txt
  - tests/fixtures/cursor_models_auth_failed.txt
  - tests/fixtures/cursor_models_empty.txt
  - tests/gsd_curated_eval.py
  - tests/test_ai_kit_gsd_curated_config.py
  - tests/test_ai_kit_gsd_curated_config_matrix.py
  - tests/test_ai_kit_spec.py
  - tests/test_ai_kit_spec_routing.py
  - tests/test_ai_kit_spec_runtimes_table.py
  - tests/test_curated_config_apply.py
  - tests/test_curated_config_e2e.py
  - tests/test_curated_config_inventory.py
  - tests/test_curated_config_script.py
  - tests/test_cursor_agents.py
  - tests/test_gsd_curated_eval.py
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-10-19
**Depth:** deep (standard per file, plus cross-file tracing of detection -> routing -> runner dispatch)
**Files Reviewed:** 37 (the 36 files in `git diff 782d477 HEAD -- . ':!.planning'` plus the rendered `.planning/scripts/cross-ai.mjs`)
**Status:** issues_found

## Summary

I traced the D-09/D-10 contract across Python detection (`detection.py`, `routing.py`) and the
runner's dispatch (`cross-ai.mjs` template 5, rendered copy byte-identical apart from the
stamp and CONFIG). The guarded `agent` scan-all logic agrees on *which* binary wins. The
model-listing parser does not. Phase 21 made the Python parser token-based (D-10). The
runner's preflight parser stayed `" - "`-based. Python inventory can therefore list a model
that the runner then rejects as `bad_model` (CR-01). There are also smaller issues:
- a relative `./agent` path is persisted into the global runtimes cache (the runner always
  resolves to an absolute path)
- routing's cached-path fallback skips the guard
- two parser tests pass for the wrong reason because of double-escaped literals
- the new `~/.cursor/agents` and `~/.cursor/skills` protection checks names only

Labels (`_LABEL_CURSOR`, SKILL.md cursor row, README) match the evidence in
21-SMOKE-CURSOR.md and keep the interactive step marked pending. I found no overclaim there.
No test reads the real HOME. `tests.test_ai_kit_spec_runtimes_table` and `tests.test_cursor_agents`
pass (66 tests).

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Runner preflight parser disagrees with detection on nameless cursor models (D-09/D-10 split)

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:657-666` (used at `:2957-2967`); rendered copy `.planning/scripts/cross-ai.mjs` same lines
**Issue:** D-10 (21-CONTEXT.md) holds that a nameless listing line such as `auto (current, default)`
is a real format. 21-RESEARCH.md source-inspected the bundle formatter
`${id}${name ? " - " + name : ""}${flags ? " (current, default)" : ""}` and confirmed it.
`parse_cursor_models` (`detection.py:312`) keeps such ids. The runner's `parseCursorListingIds`
still skips any line without `" - "`, and it does not strip ANSI. I checked both parsers
directly on the same input:

```
input: "Available models\n\nauto (current, default)\ncomposer-2.5 - Composer 2.5\n"
python parse_cursor_models -> ['auto', 'composer-2.5']
js parseCursorListingIds  -> ["composer-2.5"]
js on "\x1b[1mcomposer-2.5\x1b[0m - Composer" -> ["\u001b[1mcomposer-2.5\u001b[0m"]
```

So inventory and recommend can offer a cursor model that the runner preflight
(`!listing.ids.includes(listed)`) then rejects as `bad_model`. The run falls through to the
next CLI or fails. The rendered runner bakes `"cursor": "auto"`, so a session where `auto`
is the nameless current/default model hits this directly. The template was bumped to 5 in
this phase, but the parser fix was applied to only one side. No parity test exists.
**Fix:** Port the D-10 rule into the template and add a fixture-parity test that runs both
parsers on `tests/fixtures/cursor_models.txt` plus the nameless and ANSI cases:
```js
const ANSI_RE = /\x1b\[[0-9;?]*[A-Za-z]/g;
const CURSOR_LINE = /^([A-Za-z0-9._-]+)(?: - .*| \((?:current|default|current, default)\))?$/;
function parseCursorListingIds(stdout) {
  if (typeof stdout !== 'string') return null;
  const ids = [];
  for (const raw of stdout.replace(ANSI_RE, '').split('\n')) {
    const ln = raw.trim();
    if (!ln || ln === 'Available models' || ln.startsWith('Tip:')
        || ln === 'No models available for this account.') continue;
    const m = CURSOR_LINE.exec(ln);
    if (m) ids.push(m[1]);
  }
  return ids;
}
```
Re-render `.planning/scripts/cross-ai.mjs` after the change. This changes the body
sha256, so check whether TEMPLATE_VERSION needs to move to 6 for already-rendered runners.

## Warnings

### WR-01: Python persists a relative `./agent` (or bare `agent`) path; the runner resolves absolute

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:184-187, 1045`; `routing.py:274-284`
**Issue:** For an empty PATH segment, `_guarded_hits` calls `which_fn(name, path=os.curdir)`, which
returns `./agent`. When the cwd segment comes first, plain `shutil.which` returns a bare
`agent` (verified: `shutil.which('agent', path=':/x')` returns `'agent'`). The tests pin this
(`test_trailing_empty_path_segment_is_the_cwd` and `test_empty_path_scans_the_cwd` expect
`./agent`). The runner uses `path.resolve` and gets an absolute path. The relative `path` is
written into the global `runtimes.json` (`cache_base`, 30-day TTL). `routing.py:278` later
reuses it from a different cwd, where it names a different file or nothing. A bare `agent`
handed to `subprocess` is also re-resolved through PATH, so the guard result can be lost.
`real_path` is computed against the cwd at detection time, so `path` and `real_path` can
disagree.
**Fix:** Return `os.path.abspath(found)` from `resolve_runtime_binary` for every hit, or at
least for guarded ones, to match the runner's `path.resolve`. Update the two tests to expect
`os.path.join(cwd_dir, "agent")`.

### WR-02: Routing's cached-path fallback bypasses the `agent` guard

**File:** `skills/ai-kit-spec-review/ai_kit_spec/routing.py:274-284`
**Issue:** When `resolve_runtime_binary` returns None, the cached `before["path"]` is reused as the
cursor binary without re-checking `_GUARDED_BINARIES`. Example: the cache recorded
`~/.local/bin/agent` (cursor), then `cursor-agent` was removed or the symlink was retargeted
to another CLI's `agent`. Resolution then correctly fails, but the fallback revives the stale
path. It records the new non-cursor `real_path` it just computed and calls
`list_runtime_models("cursor", that_path)`, so the other CLI's `agent` runs with `models`.
D-02/D-09 forbid exactly this. The fallback predates this phase, but this phase added the
`real_path` that exposes the mismatch, and nothing checks it.
**Fix:** After the fallback, keep the cached path only if it still exists and, for a guarded
basename, still passes the guard:
```python
if binary and os.path.basename(binary) in _GUARDED_BINARIES and \
        os.path.basename(os.path.realpath(binary)) != _GUARDED_BINARIES[os.path.basename(binary)]:
    binary = None
```
A cleaner option is a small `detection.binary_still_valid(rid, path)` helper that routing calls.

### WR-03: ANSI and non-ASCII parser tests are vacuous (double-escaped literals)

**File:** `tests/test_ai_kit_spec.py:1554-1556, 1569-1570`
**Issue:** The literals are `"\\x1b[2mAvailable models\\x1b[0m..."` and `"m\\u00f6del - X"`
in normal (non-raw) strings. They contain a literal backslash, not ESC or `ö`. The ANSI
test passes because the escaped header counts as unrecognized and `auto (...)` still parses.
`_ANSI_RE` is never exercised. The non-ASCII test passes because `\` falls outside
`[A-Za-z0-9._-]`, not because `ö` does. Both tests would stay green if ANSI stripping were
deleted or the id class widened to Unicode `\w`. The plan's verify command
(21-01-PLAN.md:431) uses real escapes, but the committed tests do not.
**Fix:** Use `"\x1b[2mAvailable models\x1b[0m\n\nauto (current, default)\n"` and
`"mödel - X"`. Add a case that only passes if stripping works, for example
`"Available models\n\n\x1b[1mcomposer-2.5\x1b[0m - C\n"` returning `["composer-2.5"]`.

### WR-04: `~/.cursor/agents` and `~/.cursor/skills` are protected by names only

**File:** `tests/gsd_curated_eval.py:227-228`; pinned by `tests/test_gsd_curated_eval.py` `test_cursor_agents_skills_hooks_are_protected`
**Issue:** The protected-set snapshot uses `_dir_names` for the new cursor directories. So an
installer or apply that overwrites an existing `~/.cursor/agents/gsd-*.md`, or retargets a
symlinked skill, passes as "protected set unchanged". The equivalent codex directory uses
`_tree_sha` (`:316`). The test asserts the blind spot ("changed" content gives `strict == []`)
instead of protecting against it. This weakens the core no-real-HOME-writes guarantee for the
cursor smoke.
**Fix:** Use `_tree_sha(home / ".cursor" / "agents")` and `_tree_sha(home / ".cursor" / "skills")`
(or `_tree_sha` alongside the name listing), and flip the test to expect a strict change on
content edits.

### WR-05: Seam-sniffing `inspect.signature` silently disables the D-09 scan; `path_env` is half-plumbed

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:169-200, 203-208`
**Issue:**
- (a) `_guarded_hits` inspects `which_fn`'s signature and skips the scan-all entirely when the
  callable has no `path` or `**kwargs` parameter. Detection then quietly falls back to
  first-hit, which is the behavior D-09 replaced. Every test lambda had to change to
  `**_kwargs` because of this, and a future seam that forgets it gets wrong results with no
  error.
- (b) The first hit always comes from `which_fn(name)` against `os.environ["PATH"]`, even when
  `path_env` is supplied. One resolution therefore mixes two PATHs.
- (c) `path_env` is accepted by `resolve_runtime_binary` but not by `detect_installed_clis` or
  `build_runtimes_snapshot`. Any test that injects a fake `which_fn` there scans the
  developer's real PATH entries, which is a test-isolation leak.
**Fix:** Drop the introspection and the separate first hit. Iterate
`(path_env if path_env is not None else os.environ.get("PATH", "")).split(os.pathsep)` and call
`which_fn(name, path=d or os.curdir)` unconditionally, with the `which_fn` contract documented
as "must accept `path=`". Thread `path_env` through `detect_installed_clis` and
`build_runtimes_snapshot`.

### WR-06: Any single-token non-listing line is accepted as a cursor model id

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:307-333`
**Issue:** The optional suffix group in `_CURSOR_MODEL_LINE` lets a bare token match. Nothing
requires the `Available models` header. So exit-0 output like `Loading...`, `Error` or
`Unauthorized` becomes a "verified" model listing (verified: `parse_cursor_models("Loading...\n")`
returns `['Loading...']`). The docstring promises None for unrecognized output. This
overstates certainty in the inventory (AGENTS.md no-overclaim rule) and feeds recommend.
**Fix:** Require the `Available models` header before accepting any id (return None if no
header was seen and no `" - "` line matched), or accept a bare token only after the header:
```python
seen_header = False
...
if line == "Available models": seen_header = True; continue
...
if match and (seen_header or " - " in line): models.append(match.group(1))
```

## Info

### IN-01: `~/.cursor/hooks.json` is added to the strict set twice

**File:** `tests/gsd_curated_eval.py:212` and `:314`
**Issue:** `_strict_files` already hashes it. The explicit `strict[...] = _file_sha(cursor / "hooks.json")` overwrites the same key with the same value.
**Fix:** Delete the line at `:314` and the `cursor` local at `:308`.

### IN-02: `CURSOR_CLI_CONFIG_LABEL` duplicates the literal it is meant to match

**File:** `tests/gsd_curated_eval.py:210, 338`
**Issue:** If either f-string drifts, `--host-rewrite` silently stops matching the strict label.
**Fix:** Define the constant before `_strict_files` and use it at `:210`.

### IN-03: `pathHits` duplicates `which`'s loop

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:404-419`
**Issue:** Two copies of the same PATH walk and its empty-segment comment.
**Fix:** `function which(bin, envPath) { if (bin.includes('/')) ...; return pathHits(bin, envPath).next().value ?? null; }`

### IN-04: `test_files_parse_with_the_bundle_rules` cannot fail on an unparseable file

**File:** `tests/test_cursor_agents.py:62-65`
**Issue:** It loops only over `_parsed_agents()`, which already drops files that fail to
parse. The pins test catches a dropped file only indirectly.
**Fix:** Iterate `_agent_files()` and `assertIsNotNone(parse_agent(...))`.

### IN-05: Scan-all widens acceptance of a repo-planted `agent` under an empty PATH segment

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:425-439`; `detection.py:184-187`
**Issue:** With an empty PATH segment, a checkout can ship `agent -> x/cursor-agent` (the guard
checks only the basename). Previously a legitimate earlier `agent` blocked it. Now the scan
continues and picks it, and cursor exec runs with `--force --sandbox disabled`. The
precondition, an empty PATH segment, already allowed unguarded `cursor-agent` from the
cwd, so the new exposure is marginal. It is still worth a line in runner.md.
**Fix:** Document it, or skip empty and relative PATH segments for the guarded name.

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
