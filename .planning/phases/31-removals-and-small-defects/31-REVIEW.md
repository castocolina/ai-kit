---
phase: 31-removals-and-small-defects
reviewed: 2026-11-06T18:00:16Z
depth: standard
files_reviewed: 85
files_reviewed_list:
  - .pre-commit-config.yaml
  - Makefile
  - pyproject.toml
  - skills/_shared/ai_kit_rules_common/tool_presence.py
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py
  - skills/ai-kit-gsd-curated-config/evals/evals.json
  - skills/ai-kit-gsd-curated-config/evals/files/v1-project/.planning/config.json
  - skills/ai-kit-gsd-curated-config/evals/trigger-queries.json
  - skills/ai-kit-gsd-curated-config/references/runner.md
  - skills/ai-kit-project-rules-agents/SKILL.md
  - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rule_checker.py
  - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py
  - skills/ai-kit-project-rules-makefile/SKILL.md
  - skills/ai-kit-session-wake/ai-kit-session-wake.py
  - skills/ai-kit-spec-config/SKILL.md
  - skills/ai-kit-spec-config/evals/evals.json
  - skills/ai-kit-spec-config/evals/files/stale-opencode/review-spec.toml
  - skills/ai-kit-spec-config/evals/trigger-queries.json
  - skills/ai-kit-spec-config/references/check-only.md
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
  - skills/ai-kit-spec-execute/SKILL.md
  - skills/ai-kit-spec-execute/evals/evals.json
  - skills/ai-kit-spec-execute/evals/files/gsd-project/.planning/PROJECT.md
  - skills/ai-kit-spec-execute/evals/files/superpowers-plan/docs/superpowers/plans/2026-11-06-demo.md
  - skills/ai-kit-spec-execute/evals/trigger-queries.json
  - skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py
  - skills/ai-kit-spec-review/ai_kit_spec/cli.py
  - skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py
  - skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py
  - skills/ai-kit-spec-review/ai_kit_spec/jsonc_read.py
  - skills/ai-kit-spec-review/ai_kit_spec/provider_check.py
  - skills/ai-kit-spec-review/ai_kit_spec/routing.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py
  - skills/markdown-to-pdf/scripts/render_mermaid.py
  - tests/test_agents_md_links.py
  - tests/test_ai_kit_gsd_curated_config.py
  - tests/test_ai_kit_project_rules_agents.py
  - tests/test_ai_kit_rules_common.py
  - tests/test_ai_kit_spec.py
  - tests/test_ai_kit_spec_check_providers.py
  - tests/test_ai_kit_spec_e2e.py
  - tests/test_ai_kit_spec_execute_router.py
  - tests/test_ai_kit_spec_goal_prompt_cli.py
  - tests/test_ai_kit_spec_gsd_tools.py
  - tests/test_ai_kit_spec_jsonc_read.py
  - tests/test_ai_kit_spec_legacy_config.py
  - tests/test_ai_kit_spec_routing.py
  - tests/test_ai_kit_spec_runner_dispatch.py
  - tests/test_ai_kit_spec_runtimes_table.py
  - tests/test_ai_kit_spec_trust.py
  - tests/test_arch.py
  - tests/test_banned_tool_mentions.py
  - tests/test_check_dogfood.py
  - tests/test_config_doctor.py
  - tests/test_config_doctor_pty.py
  - tests/test_cross_ai_runner_e2e.py
  - tests/test_cross_ai_skill_text.py
  - tests/test_curated_config_recommend.py
  - tests/test_curated_config_script.py
  - tests/test_doctor_apply_safety.py
  - tests/test_gate_scope.py
  - tests/test_install.sh
  - tests/test_quota_policy_text.py
  - tests/test_run_unittest_parallel.py
  - tests/test_runtime_list_drift.py
  - tests/test_setup.py
  - tests/test_tool_substitution_hook.py
  - tests/test_wizard_app_1.py
  - tests/wizard_fixtures.py
  - tools/check_dogfood.py
  - tools/config_doctor_appliers.py
  - tools/config_doctor_checks.py
  - tools/config_doctor_readers.py
  - tools/install.sh
  - tools/setup.py
findings:
  critical: 0
  high: 1
  medium: 2
  low: 6
  info: 5
  blocker: 1
  warning: 8
  total: 14
  necessity: 2
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-11-06T18:00:16Z
**Depth:** standard
**Files Reviewed:** 85 (added or modified, `8a74d94..HEAD`, scoped to tools/skills/tests and build config)
**Status:** issues_found

## Summary

I reviewed the priority files in full: `tools/setup.py` (the `_is_inside`, prune and headless paths),
`tools/install.sh`, `provider_check.py`, `jsonc_read.py`, `goal_prompt.py`, `check_dogfood.py`, and the
new tests (drift, rtk ban, AGENTS.md links, check-providers, jsonc drift, the setup and install tests).
The other files I read as diffs. The 85 files are the full list from
`git diff --name-only --diff-filter=AM 8a74d94..HEAD`.

What holds up:
- **Removed skills:** a search outside the history folders and `tests/fixtures/archived` finds none of
  the three removed skill, package or script names. Only `provider_check.py:7` keeps a partial
  "opencode-providers" mention.
- **Runtime rules:** the new runtime code is stdlib-only, and no new config write was added.
- **Test isolation:** the new installer tests build a fresh env with a scratch `HOME`, `XDG_*` and
  `AI_KIT_REFUSE_REAL_HOME=1`, and leave out `CLAUDE_CONFIG_DIR` and `PI_CODING_AGENT_DIR`. No new test
  writes to the real home.

The main defect:
- **CR-01 (verified):** the phase now resolves the kit dir (`pwd -P` in `install.sh`,
  `realpath(__file__)` in `setup.py`). The statusLine ownership checks still compare paths as strings
  with `normpath`. An existing install whose statusLine was written through an alias spelling now reads
  as "foreign". The headless `--with-statusline` run then refuses and exits 1, the wizard offers to
  overwrite ai-kit's own line, and `uninstall` leaves it wired. A scratch repro
  (`tmp/p31-review/repro_statusline.py`) printed `alias-spelled run: ours`, `resolved run: foreign` and
  `uninstall sees ours: False`.

The necessity rubric (`necessity-review.md`) was read. There are two necessity findings, both Info.

Severity mapping: high is BLOCKER (`CR-`); medium and low are WARNING (`WR-`); info is `IN-`.

## Critical Issues

### CR-01: Resolving the kit dir breaks statusLine ownership for installs written through an alias spelling (high, BLOCKER)

**File:** `tools/setup.py:116-117` and `tools/install.sh:293`, interacting with `tools/command_ownership.py:59-61`, `tools/setup.py:2372-2373, 2424, 2479, 2742, 2829`
**Issue:** `resolve_paths` now builds `status_line` from a resolved kit dir:
- `install.sh` exports `AI_KIT_DIR` after `pwd -P`.
- Without `AI_KIT_DIR`, `setup.py` falls back to `realpath(__file__)`.

Ownership is still decided by `rewrite_owned_command`, which compares `os.path.normpath(script)` with
`normpath(entry)` as strings. A one-line (bootstrap) install made before this phase wrote
`python3 -S $HOME/.local/share/ai-kit/tools/claude-status-line.py` without resolving the path. If any
part of `$HOME`, `XDG_DATA_HOME` or `AI_KIT_DIR` is a symlink (SPEC Background: `/home` is a symlink to
`/var/home` on this machine; macOS has `/private`), that statusLine now counts as foreign:
- `detect_statusline` reports `foreign`.
- `wire_statusline` in headless mode warns "foreign statusLine" and the run exits 1.
- The wizard asks whether to overwrite ai-kit's own entry.
- `unwire_statusline` (uninstall) leaves the statusLine pointing into the kit. It breaks once the kit is
  deleted.

The Cursor side (`_command_is_ours` at 2479) and the legacy migration (2742) take the same path. The
phase fixed alias handling for symlinks (R8), but this second consumer of `install_dir` still compares
strings.

Reproduced in a scratch dir: `env AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p31-review/repro_statusline.py`
printed `ours` / `foreign` / `False`.
**Fix:** Compare resolved script paths in the one shared parser:
```python
# tools/command_ownership.py, rewrite_owned_command
def _same_file(a, b):
    return os.path.normpath(os.path.realpath(a)) == os.path.normpath(os.path.realpath(b))

if script_index is not None and _same_file(script, old_entry):
    argv[script_index] = new_entry
    return shlex.join(argv)
```
Keep the `.backup`/`.bak` refusal ahead of the comparison. Add a scratch test: wire through an alias
`AI_KIT_DIR`, then run `detect_statusline`, `wire_statusline` (headless) and `unwire_statusline`
through the resolved spelling. All three must treat the line as ours.

## Warnings

### WR-01: A non-ENOENT error in the new headless prune aborts the whole install with a traceback (medium)

**File:** `tools/setup.py:1415-1421, 1486-1493, 1527-1536, 4820-4823`
**Issue:** `cmd_install_headless` now runs `_headless_prune_roots` before anything else, for every
headless install or reconfigure, including `--skills X`. `unlink_one` only suppresses
`FileNotFoundError`. A `PermissionError` or other `OSError` from `os.remove` propagates through
`apply_stale_prune`, `_prune_headless` and `_headless_prune_roots` into `main()` without being caught.
Examples: a read-only or root-owned skills dir, or an immutable flag on a link. A cleanup step the user
never asked for then kills the requested linking with a Python traceback. Before this phase, headless
runs never pruned. Every other headless step reports failures as a `warn:` line plus exit 1, and keeps
going.
**Fix:** Catch `OSError` per link in `_prune_headless`, warn and continue, and fold the failure into the
run's exit code:
```python
def _prune_headless(root, stale, dry, counts):
    ok = True
    for item in sorted(stale):
        print(f"warn: removing dead ai-kit link {item} (entry removed upstream)", file=sys.stderr)
        try:
            apply_stale_prune(root, [item], dry, counts)
        except OSError as exc:
            print(f"warn: could not remove {item}: {exc}", file=sys.stderr)
            ok = False
    return ok
```
Have `_headless_prune_roots` return `ok`, and set `ok = False` in `cmd_install_headless` when it fails.

### WR-02: A listing with no `provider/model` lines turns every reference into a confirmed stale warning (medium)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/provider_check.py:150-155`
**Issue:** `detect_opencode_models` returns every non-blank stdout line of an exit-0 run.
`served_providers` keeps only lines that contain `/` (`ids = {...}`), then checks `if listed:` against
the raw list, not against `ids`. Suppose stdout holds only non-model text, such as a banner, a migration
notice or a changed output format (2.x is in flux, and Phase 35 owns that). Then `ids` is empty, but the
code still reports `served providers: listed by opencode ()` with `confirmed=True`. It also warns that
every opencode reviewer and catalog entry is stale, with no "unconfirmed" qualifier. That presents
inferred results as verified, which AGENTS.md and the SPEC both forbid. Only the `listed == []` case
says "not checked".
**Fix:** Decide on the parsed ids:
```python
if listed is not None:
    ids = {line.split("/", 1)[0] for line in listed if "/" in line}
    if not ids:
        return None, "not checked: opencode listed no models", True
    extra = _names_from(jsonc_read.project_config_paths(cwd)) - ids
    ...
```
Add a test with a fake listing such as `"Loading...\n"` and exit 0.

### WR-03: The `cd` in `install.sh` is not guarded against CDPATH, so a relative `AI_KIT_DIR` can corrupt `INSTALL_DIR` (low)

**File:** `tools/install.sh:293`
**Issue:** `INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd -P)"` runs inside a command substitution. When
`CDPATH` is set and `INSTALL_DIR` is a relative name (`AI_KIT_DIR=ai-kit AI_KIT_SKIP_FETCH=1`), bash's
`cd` prints the directory it found to stdout. The substitution then captures two lines, and setup.py is
exec'd at a broken path. The same file already guards this case at line 82 (`>/dev/null 2>&1`). The
`[ -d ]` test also cannot fail here, because line 289 already required
`$INSTALL_DIR/tools/setup.py` to exist.
**Fix:** `INSTALL_DIR="$(CDPATH= cd -- "$INSTALL_DIR" >/dev/null 2>&1 && pwd -P)"` (and drop the
redundant `-d` test, or keep it as documentation).

### WR-04: `check-providers` can exit 2, but both docs say it "exits 0 whatever it finds" (low)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/cli.py:420-424`, `skills/ai-kit-spec-review/ai_kit_spec/provider_check.py:173-175`
**Issue:** `config_io.cfg_global_path(env)` raises `ConfigError` when `HOME` or `XDG_CONFIG_HOME` is not
absolute, and `_cmd_check_providers` does not catch it. Plan 02's summary records the resulting exit 2
as a known gap. But `skills/ai-kit-spec-config/SKILL.md` (Step 1) and `references/check-only.md` tell
the agent this step "exits 0 whatever it finds, so it never stops setup". SPEC R5 also says the report
"never blocks". An agent that follows the doc may treat the exit 2 as a setup failure.
**Fix:** In `_scan_sources`, catch `ConfigError` for the global path and report that source as
`unavailable (<reason>)` instead of failing. Alternatively, catch it in `_cmd_check_providers`, print a
`not checked:` line and return 0. Add a test with `XDG_CONFIG_HOME=relative`.

### WR-05: The JSONC drift test treats "both readers failed" as agreement and only compares behaviour (low)

**File:** `tests/test_ai_kit_spec_jsonc_read.py:76-82`
**Issue:** `sorted(jsonc_read.read_provider_names(path) or [])` is compared with
`sorted(_doctor_names(path) or [])`. A fixture that both readers reject (`None`) therefore passes as a
match, exactly like a fixture with no providers. The guard also runs only five fixtures. It never
compares the copied scanner functions themselves (`_classify*`, `strip_jsonc_comments`,
`code_indices`, `strip_trailing_commas`). So a change to the doctor's scanner on paths those fixtures
miss goes unnoticed. Examples: a backslash run before a closing quote, or a `*/` inside a string. That
weakens the "copy plus drift test" pattern (29 D-13) the module relies on.
**Fix:** Assert that each fixture parses (`assertIsNotNone` on both sides) before comparing. Also add a
source-level check, for example comparing `inspect.getsource` of each shared scanner function after
stripping docstrings, so any edit to one copy fails until the other matches.

### WR-06: Bare `--headless` reports "nothing requested" after removing links, and a dry run prints "removing" (low)

**File:** `tools/setup.py:1498-1500, 4728-4730, 4863-4865`
**Issue:** A bare `install --headless` can now delete links, but `_headless_summary` still prints
`headless: nothing requested — pass --skills/... to link or wire something`, and `counts["pruned"]`
appears in no summary. Under `--dry-run`, every candidate prints
`warn: removing dead ai-kit link …`, and then `(dry-run — no changes were made)`. Both outputs
misdescribe what happened.
**Fix:** Print `would remove` when `dry` is set. Have `_headless_summary` add
`{counts['pruned']} dead links pruned` whenever `pruned > 0`, including the not-requested branch.

### WR-07: The AGENTS.md link test passes link targets to git without `--`, and treats an out-of-repo target as not ignored (low)

**File:** `tests/test_agents_md_links.py:23-29, 42-45`
**Issue:**
- **No `--`:** `git check-ignore -q <target>` puts no `--` before the target. A link written as
  `-x.md` would be read as an option.
- **Out-of-repo target:** a link that resolves outside the repo (`../other/file.md`) makes
  `check-ignore` exit 128 ("outside repository"). `is_ignored` reads that as "not ignored", so the link
  passes silently.

The test is meant to catch links readers cannot follow. A link outside the checkout is exactly such a
link.
**Fix:** Use `["git", "-C", root, "check-ignore", "-q", "--", target]`. Treat a return code other than
0 or 1 as a failure (`(unverifiable)`). Also flag a target whose resolved path leaves `repo_root`.

### WR-08: Origin comments still name deleted modules and their line numbers (low)

**File:** `tools/config_doctor_appliers.py:150-152, 314`; `skills/ai-kit-spec-review/ai_kit_spec/provider_check.py:7`
**Issue:** SPEC R3 says each origin comment is reworded "so it names no deleted file". The comments
listed below still cite deleted modules. Readers cannot follow these references any more, and the R3
search misses them because it only matches the skill names.
- **`config_doctor_appliers.py:150-152`:** cites line ranges (`_classify lines 30-88`, …,
  `significant_indices 251-272`) that only existed in the deleted `jsonc_edit.py`.
- **`config_doctor_appliers.py:314`:** still says `Generalizes jsonc_edit.find_provider_object's …`.
- **`provider_check.py:7`:** names `cross_reference.py`.
**Fix:** Drop the line numbers and the deleted module names, for example: "JSONC surgical helpers
(format mechanics only); the read-only scanner is drift-tested against
`skills/ai-kit-spec-review/ai_kit_spec/jsonc_read.py`".

## Info

### IN-01: Formatting slip in `cmd_install_headless`

**File:** `tools/setup.py:4834`
**Issue:** `replaced =(_headless_replace(...)`: there is a missing space, and the continuation indent is
now off by one. This crept in when the `counts` line was moved.
**Fix:** `replaced = (_headless_replace(paths, entries, skills_flag, dry, counts)`.

### IN-02: Generality without instantiation: `ReadContext.runner` / `build_catalog(runner=)` has no reader left

**File:** `tools/config_doctor_checks.py:1173, 1186, 1193`
**Category:** necessity
**Issue:** The only reader that used `ctx.runner` was `read_rtk_cursor_integration`, which this phase
removed. A search for `ctx.runner` in `tools/` finds nothing. The parameter is still passed around, and
tests still pass it (`tests/test_config_doctor.py:831`). Plan 06 kept it on purpose "because 30.1 builds
on them", but 30.1 is already in this tree and uses nothing from it. This is judgment, because a future
reader may want it.
**Fix:** Remove the parameter and its plumbing, or leave a `shortcut:` comment naming the planned
consumer.

### IN-03: Impossible-state guard: `except ValueError` in `_is_inside`

**File:** `tools/setup.py:1192-1195`
**Category:** necessity
**Issue:** `os.path.commonpath` raises `ValueError` only when it mixes absolute and relative paths, or
paths on different drives (Windows). Both arguments come from `os.path.realpath`, which always returns
absolute paths. The installer is POSIX-only (it relies on symlinks and bash). So the branch cannot run.
It is harmless.
**Fix:** Remove the try/except, or comment why it is kept.

### IN-04: The rtk ban misses identifier forms, and the usage-metrics check only catches backticked subcommands

**File:** `tests/test_banned_tool_mentions.py:14-15`
**Issue:** `\brtk\b` does not match `rtk_history` or `RTK_SIGNAL`, because `_` is a word character. So
a future `RTK_*` constant or `rtk_*` helper outside the exemptions passes the ban. The SPEC's
whole-word wording technically allows this, but it is not the intent. `USAGE_INVITES` catches
`` `rtk gain` `` but not `run rtk gain` without backticks.
**Fix:** Use `(?<![A-Za-z0-9])rtk(?![A-Za-z0-9])`, so `_` and `-` count as boundaries. Widen
`USAGE_INVITES` to `\brtk\s+(?:init|gain|discover|[a-z][\w-]*)\b` when it follows a verb such as
run/use/execute.

### IN-05: The same `@file:` gap remains in another gsd-tools JSON parser

**File:** `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:312`
**Issue:** `config_get` still runs `json.loads(result.stdout)` on gsd-tools output. R11 scoped the fix
to goal-prompt, and config-get replies are small, so this is unlikely to trigger today. Still, it is the
same reply format with no handling.
**Fix:** If it ever matters, move `_load_gsd_reply`'s logic into a shared spec-review helper and use it
here.

---

_Reviewed: 2026-11-06T18:00:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
