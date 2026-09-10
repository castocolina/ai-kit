---
phase: 02-opencode-provider-management
reviewed: 2026-09-09T21:42:26Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - skills/ai-kit-opencode-providers/ai-kit-opencode-providers.py
  - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/__init__.py
  - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py
  - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/jsonc_edit.py
  - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py
  - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py
  - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py
  - tests/test_ai_kit_opencode_providers.py
  - skills/ai-kit-opencode-providers/SKILL.md
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-09T21:42:26Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the `ai-kit-opencode-providers` skill: a small stdlib-only Python CLI (`list`/`remove`) that surgically edits the `"provider"` block of `opencode.jsonc` via a hand-rolled comment/string-aware JSONC scanner, plus a mode-preserving atomic writer and a non-blocking cross-reference scanner over review-spec/catalog files. The test suite (60 tests, all passing) is unusually thorough for comma placement, comment preservation, symlink handling, non-UTF-8 input, duplicate ids, and non-object provider values, and the atomic-write/symlink-preservation paths behave correctly for well-formed input.

However, direct testing against a *malformed* (brace-unbalanced) but otherwise ordinary-looking `opencode.jsonc` found that `remove` silently deletes bytes belonging to an ancestor object — not just the target provider entry — and then overwrites the real config file, exits 0, and prints `removed provider "..." ...` as if nothing went wrong. This is exactly the failure mode the project's stated core value calls out ("ai-kit must never corrupt uz's AI-CLI configuration and must never claim more certainty than it has"), and there is no pre-flight or post-edit structural validation anywhere in the write path to catch it. This is the headline finding below (CR-01). The remaining findings are lower-severity robustness gaps in the atomic writer and a couple of quality/UX nits.

## Critical Issues

### CR-01: `remove` can silently corrupt an already-malformed config and reports success anyway

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/jsonc_edit.py:137-152` (`find_object_span`), `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/jsonc_edit.py:349-393` (`remove_provider`), `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py:52-73` (`cmd_remove`)

**Issue:** `find_object_span` locates the end of a provider entry's value purely by brace-depth counting from that entry's own opening `{`, with no awareness of whether the braces it counts actually belong to that entry. If the document has one fewer closing brace than opening brace anywhere before the target entry finishes (a very plausible real-world state — a half-finished hand edit, a crash mid-write by some other tool, a copy/paste that dropped a `}`), the scanner walks straight through the target entry's *intended* end and consumes the next `}` it finds — which may belong to the enclosing `"provider"` object or the document root. `remove_provider` then deletes `key_start..value_end` using that wrong `value_end`, and `cmd_remove` writes the result straight to disk via `write_preserving_mode` with no validation step in between. The command exits `0` and prints `removed provider "X" from PATH`.

Reproduced directly against the shipped code:

```python
text = (
'{\n'
'  "provider": {\n'
'    "a": { "npm": "x" },\n'
'    "broken": { "npm": "y"\n'
'  }\n'
'}\n'
)
# missing brace: "broken"'s value object never closes on its own
```

Running `cmd_remove(..., provider_id="broken", ...)` against a file containing exactly this text:
- exit code: `0`
- stdout: `removed provider "broken" from <path>`
- file on disk after the call: `'{\n  "provider": {\n    "a": { "npm": "x" }\n    \n}\n'`
- `json.loads()` on that output: `json.decoder.JSONDecodeError: Expecting ',' delimiter: line 6 column 1 (char 49)`

The `}` that was supposed to close `"provider"` got eaten as if it belonged to `"broken"`'s value, and the resulting file — which the tool just claimed to have successfully edited — is no longer valid JSON at all, with both the `"provider"` object and the document root now unterminated. Nothing in the tool detects or reports this; the user's config is simply left broken with an apparently-successful CLI run in their scrollback. There is no test in `tests/test_ai_kit_opencode_providers.py` covering unbalanced/malformed brace structure for `remove` (the existing "malformed" tests — e.g. `test_malformed_entry_renders_dashes` — only cover `list` against a *balanced* but JSON-invalid leaf value, which is a different and much safer failure mode since `list` never writes).

**Fix:** Add a structural guard before `write_preserving_mode` is called in `cmd_remove` (and equivalently before any future write path): verify the whole document's brace balance is unaffected outside the deleted span, and/or verify the post-edit text still round-trips through `json.loads(strip_trailing_commas(strip_jsonc_comments(result)))` with the same top-level key set minus the removed id. If validation fails, abort with a non-zero exit and an explicit "the config could not be safely edited, no changes were written" message rather than writing. At minimum, assert that the computed `value_end` for the *target* entry is bounded by (not equal to or past) the end of the parent `"provider"` object's own span (`find_provider_object`'s `close_i`), and refuse to remove if it is not — this alone would have caught the repro above without requiring a full JSON re-parse.

```python
# cli.py, cmd_remove, before write_preserving_mode(path, result):
if not looks_structurally_sound(text, result, args.provider_id):
    print(f"error: refusing to write a structurally unsound edit to {path}", file=err)
    return EXIT_ERROR
```

## Warnings

### WR-01: Atomic writer never fsyncs before `os.replace`

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py:20-25`

**Issue:** `write_preserving_mode` writes the new content to a temp file and calls `os.replace(tmp, target)` without ever calling `os.fsync()` on the temp file descriptor (or the containing directory) first. `os.replace` is atomic with respect to concurrent readers, but on a crash/power-loss shortly after the call returns, the filesystem may not yet have persisted the temp file's data blocks even though the rename metadata was journaled — the config can end up truncated or zero-length after recovery. Given this tool's stated bar ("must never corrupt"), durability across a crash immediately following a successful `remove` is part of that bar, not just consistency during concurrent reads.

**Fix:**
```python
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write(text)
    handle.flush()
    os.fsync(handle.fileno())
os.chmod(tmp, mode)
os.replace(tmp, target)
dir_fd = os.open(dirname, os.O_RDONLY)
try:
    os.fsync(dir_fd)
finally:
    os.close(dir_fd)
```

### WR-02: File ownership (uid/gid) is silently dropped on replace

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py:10-29`

**Issue:** The writer preserves the permission bits (`stat.S_IMODE`) but not the owner/group of the original file. `tempfile.mkstemp` creates the temp file owned by the current process's uid/gid; after `os.replace`, the config file's ownership silently becomes whatever the running process's uid/gid is. If `opencode.jsonc` was created or is expected to be owned by a different user/group than the one invoking this tool (e.g. a config deployed by a provisioning step, or edited via `sudo`), a `remove` call quietly changes ownership with no warning — a real, if narrow, "corrupts the config's attributes" case for this project's stated risk surface, distinct from content corruption.

**Fix:** Capture `os.stat(target).st_uid` / `st_gid` alongside the mode, and `os.chown(tmp, uid, gid)` before `os.replace`, falling back gracefully (log/ignore) when the process lacks permission to chown (e.g. non-root changing to a different uid), since failing the whole remove for a chown permission error would be worse than leaving ownership as-is only in that specific privilege-denied case.

### WR-03: Cross-reference "not active" framing can be misread as "removal is safe"

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py:38-51`

**Issue:** When the local review-spec sets `strategy = "local-only"`, a hit in the *global* review-spec is printed with `(not active: local review-spec sets strategy = "local-only")`. This is documented behavior (SKILL.md explicitly warns against relaying this as "safe"), and it's a deliberate, well-tested design choice — but the qualifier is only ever attached to the *global* tier per the current `inactive` set (`{src for src, status in audit if status == "scanned-inactive"}`), computed once from `collect_references`'s three fixed sources in fixed order. If a future maintainer adds a fourth source to `collect_references` without also updating the `inactive`-detection logic in `cmd_remove` (which currently special-cases only the "global tier under local-only" condition via the audit status string), a similarly-conditional source could silently lose its "not active" qualifier. This is a maintainability/coupling risk rather than a bug today.

**Fix:** Derive "inactive" generically from the audit tuple's status (`status == "scanned-inactive"`) for *any* source, which the code already does — but consider deriving the human-readable qualifier text from the source's role/reason rather than hardcoding the `local-only` strategy wording in `cmd_remove`, so a new conditional-activation source doesn't require touching unrelated string-formatting code to stay correct.

### WR-04: `argparse` subcommands ship with no `--help` text

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py:118-139`

**Issue:** `parser`, `p_remove`, and `p_list` are all constructed with no `description`/`help` strings, and neither positional/optional argument documents itself (`provider_id`, `--config`). Running `ai-kit-opencode-providers.py --help` or `... remove --help` produces a bare usage line with no explanation of what `--config` expects (a *file* path, not a directory — a distinction the SKILL.md calls out explicitly as easy to get wrong) or what happens on a missing id. Since this CLI's primary caller is an agent skill reading SKILL.md rather than a human running `--help`, this is low-stakes, but it's a real gap if the tool is ever invoked directly by a person.

**Fix:** Add `description=` to the parser and `help=` to each argument, e.g. `p_remove.add_argument("--config", default=None, help="full path to opencode.jsonc (not a directory); defaults to $OPENCODE_CONFIG_DIR or $XDG_CONFIG_HOME/opencode/opencode.jsonc")`.

## Info

### IN-01: Substring cross-reference matching can produce confusing warnings

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py:57-59, 82-93`

**Issue:** `scan_review_spec`/`scan_catalog` match with plain Python `in` (substring containment), so removing a provider id that happens to be a substring of an unrelated value (or that equals a runtime name like `opencode`/`codex`) produces warnings unrelated to the actual provider. This is explicitly documented as intentional in SKILL.md ("Over-warning is the deliberate direction for a non-blocking check") and is well covered by tests, so it is not a defect — flagging only because it's worth double-checking this stays purely informational (never gates removal) as the tool evolves; today it correctly never blocks.

**Fix:** No action required; consider only if a future change makes any cross-reference result gate behavior.

### IN-02: `ai-kit-opencode-providers.py` has a shebang but is not executable

**File:** `skills/ai-kit-opencode-providers/ai-kit-opencode-providers.py`

**Issue:** The file starts with `#!/usr/bin/env python3` but has mode `644`, not `755`. It's always invoked as `python3 "$TOOLS_PY" ...` per SKILL.md, so this has no functional effect today, but the shebang implies direct execution (`./ai-kit-opencode-providers.py ...`) which will currently fail with "Permission denied".

**Fix:** Either `chmod +x` the file to match the shebang's implication, or drop the shebang line since it's misleading given how the tool is actually invoked.

### IN-03: `__init__.py` is fully empty with no module docstring

**File:** `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/__init__.py`

**Issue:** Every other module in the package (`atomic_write.py`, `cli.py`, `jsonc_edit.py`, `config_paths.py`, `cross_reference.py`) opens with a one-line module docstring describing its responsibility. `__init__.py` has zero content, which is functionally fine (it's just a package marker) but is a minor inconsistency with the rest of the package's documentation style.

**Fix:** Optional: add a one-line docstring, e.g. `"""ai-kit-opencode-providers: list/remove config-based opencode providers."""`.

---

_Reviewed: 2026-09-09T21:42:26Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
