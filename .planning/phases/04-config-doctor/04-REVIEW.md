---
phase: 04-config-doctor
reviewed: 2026-09-10T05:47:13Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - tools/config_doctor_checks.py
  - tools/config_doctor_readers.py
  - tools/config_doctor_app.py
  - tools/config_doctor_appliers.py
  - tools/setup.py
  - tests/test_config_doctor.py
  - tests/test_config_doctor_pty.py
  - Makefile
  - .pre-commit-config.yaml
  - pyproject.toml
  - README.md
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-09-10T05:47:13Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the Config Doctor Checks Catalog engine (readers, checks, appliers), the
Textual review/apply screen, `setup.py`'s `--config-doctor` entry point, both test
modules, and the four gate-registration files (Makefile, `.pre-commit-config.yaml`,
`pyproject.toml`, README.md).

Gate registration is genuinely correct — every claim in the SUMMARY.md files (py-compile
regex, unittest entries, pyright include, pylint/vulture exclusion) was independently
verified against the actual file contents, not just trusted. The three-state reader
contract, the JSONC surgical splice-and-self-validate path, and `apply_row`'s
exception-to-refusal conversion are all sound and match their documented invariants.

The TOML writer is the outlier: it is the one apply-eligible write path that (a) matches
its target table header with a raw substring search instead of a comment/string-aware
scan, and (b) commits bytes to the real config file *before* validating them, rather than
after — inverting the validate-then-write discipline the JSONC path (correctly) follows.
Both are fixed below. A second, independent bug in the Claude sandbox applier crashes on
a non-dict `sandbox` value in `settings.json` (caught by the generic exception handler,
so it fails closed, but surfaces a raw Python `AttributeError` string as the refusal
reason instead of a clean message). Two documentation-drift issues round out the findings.

## Critical Issues

### CR-01: `_toml_table_span` matches `[history]`-like text inside comments/strings, not just real table headers

**File:** `tools/config_doctor_checks.py:249-257`
**Issue:** `_toml_table_span` locates the `[history]` table via a raw
`text.find(f"[{table_name}]")` substring search over the *entire* file text — it is not
aware of TOML comments (`#...`) or string values. A real (and plausible) `~/.codex/config.toml`
that contains the literal text `[history]` anywhere before the real table header — e.g. a
user comment like `# see [history] below for persistence config` — causes `_toml_table_span`
to return the comment's position as the table span. `_upsert_toml_table_key` then edits
text at that wrong offset. The regex substitution inside that wrong "body" is very likely
to miss the real `persistence = ...` key (since it's actually further down, past the
computed `end`), so it falls into the *insert* branch and splices `persistence = "none"`
into the middle of arbitrary file content — between the comment and the real `[history]`
header. Because `write_toml_region_replace` only validates *syntactic* TOML (CR-02), a
splice like this can still parse as valid TOML while placing the key in the wrong
location (or, less luckily, produce outright invalid TOML) — either way it is a
real-config corruption risk on the one write path (`codex-history-persistence`) the phase
explicitly ships.

This is the direct analog of a bug the JSONC path already avoids correctly:
`config_doctor_appliers._find_top_level_key_span` uses the same comment/string-aware
`_classify()` tokenizer the readers use, so a JSONC comment or string containing `"share"`
can never be mistaken for the real top-level key. The TOML path never adopted that
discipline.

**Fix:** Anchor the table-header match to the start of a line (a real TOML table header is
always alone on its own line), so text inside a comment or a string value can never match:
```python
import re

def _toml_table_span(text, table_name):
    """Span of the table [table_name], matched only when it starts its own line.

    Line-anchored — not a bare substring search — so a comment or string value
    elsewhere in the file that happens to contain the literal text
    "[table_name]" can never be mistaken for the real table header.
    """
    match = re.search(rf"(?m)^\[{re.escape(table_name)}\][ \t]*$", text)
    if match is None:
        return None
    start = match.start()
    body_start = match.end()
    nxt = text.find("\n[", body_start)
    end = len(text) if nxt < 0 else nxt
    return start, body_start, end
```
(`re` is already imported at the top of `config_doctor_checks.py`.)

**Status: FIXED** — applied in this pass, plus a regression test
(`test_apply_codex_history_persistence_ignores_decoy_bracket_text_in_comment`) proving a
decoy `# ... [history] ...` comment above the real table no longer diverts the write.

### CR-02: `write_toml_region_replace` writes to the real target before validating

**File:** `tools/config_doctor_appliers.py:64-108`
**Issue:** The function writes `new_text` to the real `path` via `os.replace` *first*, and
only calls `tomllib.loads(new_text)` to validate it *afterward*. On a `TOMLDecodeError` it
performs a *second* atomic write to restore the previous content. This inverts the
validate-then-write discipline the sibling JSONC applier (`_apply_opencode_share_mode`)
correctly follows (it calls `_parse_jsonc_text(spliced)` and only writes via
`_atomic_write_text` if that succeeds). Two real consequences:
1. If the process is killed/crashes between the first `os.replace` (writing the
   as-yet-unvalidated text) and the second `os.replace` (restoring the original on
   failure), the user's real `config.toml` is left holding invalid TOML permanently —
   directly contradicting this phase's own stated "byte-identical refusal on malformed
   input" invariant (04-03-SUMMARY.md).
2. Between the two `os.replace` calls, any other process reading `config.toml`
   concurrently (Codex itself, another Config Doctor instance) can observe the invalid
   intermediate content, even in the non-crash case.

**Fix:** Validate `new_text` in memory before touching disk at all; only write once
validation passes. This also removes the need for the restore-on-failure path entirely,
since invalid text is never committed in the first place:
```python
def write_toml_region_replace(path, new_text):
    """Validate new_text via tomllib.loads BEFORE ever touching the target.

    Validating first (not after writing) closes the crash window a
    validate-after-write ordering would otherwise leave open: a process
    killed between "write" and "restore-on-failure" would leave the real
    target holding invalid TOML. With validate-first, invalid text is never
    written to the target at all.
    """
    try:
        tomllib.loads(new_text)
    except tomllib.TOMLDecodeError:
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    dirname = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(new_text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    return True
```

**Status: FIXED** — applied in this pass. Existing tests
(`test_write_toml_region_replace_valid_round_trips`,
`test_write_toml_region_replace_invalid_restores_original`,
`test_write_toml_region_replace_failure_leaves_target_byte_identical`) all still pass
unmodified against the new implementation (verified by re-running the suite), since they
assert observable end-state, not internal ordering.

## Warnings

### WR-01: `_apply_claude_sandbox_enabled` raises `AttributeError` on a non-dict `sandbox` value

**File:** `tools/config_doctor_checks.py:188-206`
**Issue:** When `settings.json` has `"sandbox"` present but not a dict (e.g.
`{"sandbox": "not-a-dict"}` — a real malformed-but-parseable state), the code does:
```python
if isinstance(data.get("sandbox"), dict):
    data["sandbox"] = dict(data["sandbox"])
sandbox = data.setdefault("sandbox", {})
```
`dict.setdefault` only inserts the default when the key is *absent* — since `"sandbox"`
is already present (as a string), `setdefault` returns that string unchanged. The next
line, `sandbox.get("enabled")`, then raises `AttributeError: 'str' object has no attribute
'get'`. This exception is caught by `apply_row`'s generic `except Exception` and converted
to `{"ok": False, "reason": "applier error: 'str' object has no attribute 'get'"}` — so
the app does not crash and no write occurs — but the user sees a raw Python exception
message in the confirm-modal's refusal text instead of a clean domain message, and the
non-dict case has no dedicated test coverage.
**Fix:** Normalize `sandbox` the same way the top-level `data` is normalized:
```python
def _apply_claude_sandbox_enabled(ctx, target, dry):
    path = _claude_settings_path(ctx)
    state, parsed = config_doctor_readers.read_json_checked(path)
    data = dict(parsed) if state == CONFIG_STATE_OK and isinstance(parsed, dict) else {}
    existing_sandbox = data.get("sandbox")
    sandbox = dict(existing_sandbox) if isinstance(existing_sandbox, dict) else {}
    data["sandbox"] = sandbox
    before = sandbox.get("enabled")
    sandbox["enabled"] = target
    ...
```

**Status: FIXED** — applied in this pass, plus a regression test
(`test_apply_claude_sandbox_enabled_normalizes_non_dict_sandbox_value`).

### WR-02: `setup.py --config-doctor` help text is stale — claims "read-only" after Wave 3 added apply

**File:** `tools/setup.py:2775-2778`
**Issue:** The argparse help string still reads `"launch the config diagnostics TUI
(read-only in this phase)"`. That was accurate for the Wave 1 tracer (04-01), but Wave 3
(04-03) shipped a real, explicitly-confirmed per-item apply flow (`ConfirmApplyScreen` +
`apply_row`) for four rows. A user running `setup.py --config-doctor --help` is told the
tool cannot write anything, which is no longer true.
**Fix:**
```python
parser.add_argument(
    "--config-doctor",
    action="store_true",
    help="launch the config diagnostics TUI (per-item apply, explicit confirm)",
)
```
**Status: FIXED** — applied in this pass.

### WR-03: README.md has no mention of `setup.py --config-doctor`

**File:** `README.md` (Other tools section, ~line 399-417)
**Issue:** The "Other tools" section documents `statusline-doctor.py` and the
session-start hooks, but the new `--config-doctor` flag — a new, user-facing entry point
this phase added — is entirely undocumented. A reader of the README has no way to
discover the feature exists.
**Fix:** Add a short paragraph under "Other tools" describing `setup.py --config-doctor`
(read-only catalog review + per-item, explicitly-confirmed apply for a handful of
supported settings).
**Status: FIXED** — applied in this pass.

### WR-04: Directory-fsync durability guarantee is inconsistent across the three writers

**File:** `tools/config_doctor_appliers.py`
**Issue:** `atomic_write_json` fsyncs the containing directory after `os.replace` (so the
rename itself survives a crash, per the well-known "fsync the directory too" atomic-write
requirement). `write_toml_region_replace` and `_atomic_write_text` did not do this before
this pass, despite the module docstring describing all three as sharing "the atomic-write
pattern."
**Fix:** `write_toml_region_replace`'s directory fsync is included in the CR-02 fix above.
`_atomic_write_text` fsync added in this pass:
```python
def _atomic_write_text(path, text):
    ...
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
```
**Status: FIXED** — applied in this pass.

## Info

### IN-01: `ConfigDoctorApp`'s "no config file found" empty-state branch is unreachable

**File:** `tools/config_doctor_app.py:161-166`
**Issue:** `on_mount` special-cases `if not sections:` to show "No supported AI-CLI config
file was found on this machine." As of Wave 2, `CONFIG_DOCTOR_ROWS` always contains the
`rtk-cursor-integration` row (`runtime="cross"`), and `build_catalog` unconditionally
appends the cross section whenever `matching_cross` is non-empty — which, since that list
comes from the static `CONFIG_DOCTOR_ROWS` module constant, is always true. `sections` can
therefore never actually be empty; this branch is dead code as of this phase. Not a
behavioral bug (the by-design Wave 2 outcome — the cross-runtime row should always
appear — is correct and well-tested by `TestCrossRuntimeRow`), but it is misleading
dead code that could confuse a future maintainer into thinking a true "zero rows" state
is still reachable.
**Fix:** Either remove the branch (and its test, if any relied on it) or add a one-line
comment noting it is currently unreachable given the always-present cross row, so a future
reader isn't misled. No functional risk — left as an informational note; not auto-fixed
in this pass (Info is out of default `--fix` scope).

---

_Reviewed: 2026-09-10T05:47:13Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
