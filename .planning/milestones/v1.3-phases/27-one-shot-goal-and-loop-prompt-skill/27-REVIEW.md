---
phase: 27-one-shot-goal-and-loop-prompt-skill
reviewed: 2026-10-31T16:10:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_common.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_host.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_render.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
  - skills/ai-kit-spec-goal-prompt/assets/prompt-template.md
  - skills/ai-kit-spec-goal-prompt/SKILL.md
  - skills/ai-kit-spec-goal-prompt/README.md
  - skills/ai-kit-spec-goal-prompt/references/e2e-and-evidence.md
  - skills/ai-kit-spec-goal-prompt/references/host-primitives.md
  - skills/ai-kit-spec-goal-prompt/references/strategy-matrix.md
  - tests/goal_prompt_fixtures.py
  - tests/test_ai_kit_spec_goal_prompt_cli.py
  - tests/test_ai_kit_spec_goal_prompt_common.py
  - tests/test_ai_kit_spec_goal_prompt_e2e.py
  - tests/test_ai_kit_spec_goal_prompt_evals.py
  - tests/test_ai_kit_spec_goal_prompt_golden.py
  - tests/test_ai_kit_spec_goal_prompt_host.py
  - tests/test_ai_kit_spec_goal_prompt_matrix.py
  - tests/test_ai_kit_spec_goal_prompt_render.py
  - tests/test_ai_kit_spec_goal_prompt_scope.py
  - tests/test_ai_kit_spec_goal_prompt_signals.py
  - tests/test_ai_kit_spec_goal_prompt_skilltext.py
  - tests/test_ai_kit_spec_goal_prompt_strategies.py
  - tests/test_ai_kit_spec_goal_prompt_variants.py
  - Makefile
  - .pre-commit-config.yaml
  - pyproject.toml
  - tools/run_unittest_parallel.py
findings:
  critical: 2
  warning: 6
  info: 6
  total: 14
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-10-31
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

Reviewed the eight `gp_*`/`goal_prompt.py` scripts, the template, the tests and fixtures, the
wiring diff (Makefile, pre-commit, pyproject, runner) and the SKILL/README/references for factual
errors. The tool chain is clean (ruff, pylint 10.00, pyright 0 errors, vulture silent) and the
174 tests of the render/cli/scope/common modules pass. Wiring is correct (new modules are in the
generated test groups, the e2e module is in `E2E_MODULES`, `extraPaths` added). The stdlib-only rule
holds, there are no hardcoded machine paths in the scripts, and the atomic-write helper is sound.

The real defects are behavioral and all reproduced with scratch repos under `tmp/rv/`:
`detect` executes an arbitrary repo-configured command, a non-contiguous phase list makes the
generated `/gsd-autonomous` line run phases the user did not select, and several guard/contract
holes (absolute `--out-dir`, unsanitized runner command, traceback on `OSError`, misreported
plan cycles, an unfixable `/goal` budget failure). None of these is covered by a test.

## Critical Issues

### CR-01: `detect` runs any command from the project's `.planning/config.json`

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:329-352` (called from
`goal_prompt.py:448-450`)
**Issue:** `_runner_problems` tokenizes `workflow.cross_ai_command` with `shlex.split` and
`_listing` runs `[*tokens, "--print-argv"]` whenever the LAST token's basename is `cross-ai.mjs`.
Nothing constrains the leading tokens, so a project config such as
`"cross_ai_command": "sh -c \"touch PWNED\" cross-ai.mjs"` is executed by `detect`.
Reproduced: `goal_prompt.py detect --repo tmp/rv/evil` created `tmp/rv/evil/PWNED`. This
contradicts the documented contract (`build_detect` docstring: "Read-only: nothing is written to
the project"; module docstring: "GSD only through the three read-only `query` calls") and
`gp_e2e`'s "nothing in the scanned project is executed". The skill instructs an agent to run
`detect` on whatever repo it is in, so a cloned untrusted repo gets code execution outside any
per-command permission prompt. The by-design execution of `.planning/scripts/cross-ai.mjs` is
repo-supplied code too, but the basename check is the only gate and it is trivially satisfied.
**Fix:** Only probe a runner of the exact ai-kit shape and otherwise report "usability
unverified":
```python
RUNNER_LAUNCHERS = {"node", "nodejs"}

def _listing(seams, repo, tokens):
    ok = (len(tokens) == 2 and tokens[0] in RUNNER_LAUNCHERS
          and os.path.basename(tokens[1]) == AI_KIT_RUNNER)
    if not ok:
        return None, []
    ...
```
Add a test that a `sh -c ...` command never reaches `seams.run`.

### CR-02: A non-contiguous phase list renders a `/gsd-autonomous` range that includes unselected phases

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:495-503`
**Issue:** `_autonomous_line` emits `--from {first} --to {last}` for any work set with more than
one phase. For `phases:16,18` (SKILL.md question 1 explicitly offers phase lists such as
`16,16.1,17`) the first block is `/gsd-autonomous --from 16 --to 18 --converge` while OBJECTIVE
says "Finish phases 16, 18" and ORDER lists "16, 18". Reproduced with the `opengsd-mixed`
fixture. The unattended run will plan and execute phase 17, which the user excluded. The same
happens for `16,17` when the roadmap holds `16.1` between them. No test covers a gap
(`test_single_phase_work_set_uses_only` is the only non-range case).
**Fix:** Refuse (or split) when the selected numbers are not a contiguous run of the roadmap
phases. `detect` already has the full roadmap order in `scope["order"]` / `scope["phases"]`:
```python
def _autonomous_line(work, roadmap_order):
    ...
    span = roadmap_order[roadmap_order.index(numbers[0]):roadmap_order.index(numbers[-1]) + 1]
    if span != numbers:
        raise GuardError("phases are not contiguous in the roadmap; "
                         "/gsd-autonomous cannot express a gapped set")
```
(or emit one block per contiguous run). Add a render test with a gapped set.

## Warnings

### WR-01: `--out-dir` is not held to the repo-relative rule that `answers.output_dir` gets

**File:** `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:494-499,539`;
`gp_render.py:146-149,541-547`
**Issue:** `check_fields` rejects machine paths only for `answers["output_dir"]`.
`ctx.out_dir` (the `--out-dir` flag, documented as "repo-relative directory") is only checked for
`..`. `os.path.join(repo, "/abs/dir")` returns the absolute path, so an absolute `--out-dir`
writes outside the repository. Reproduced: `render --out-dir $PWD/tmp/rv/outside` created
`tmp/rv/outside/2026-10-31-...md` and returned `"path": "../outside/..."`, while the same value in
answers fails with "field output_dir holds a machine path".
**Fix:** Validate both sources in one place:
```python
out = answers.get("output_dir") or ctx.out_dir
if out and is_machine_path(str(out), ctx.home):
    raise GuardError("field output_dir holds a machine path")
```
(or call `check_fields` with a merged mapping), and add a test for `--out-dir /tmp/x`.

### WR-02: A multi-line `cross_ai_command` injects free-form lines into the generated prompt

**File:** `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:423-428`;
`gp_sections.py:314-316`
**Issue:** `_runner_command` returns `command.strip()` with inner newlines intact and
`quota_lines` interpolates it into one rail line. A config value
`"node .planning/scripts/cross-ai.mjs\n<any text>\n\nSTOP IF"` produced a `Runner:` line followed
by unbulleted attacker-chosen lines and a fake `STOP IF (usability unverified).` heading in the
written goal file; `check_text` did not object. The file is meant to be pasted into an unattended
full-permission session, so unsanitized repo text must not become instruction lines. Because
`render` reads `detect["runner"]` from the JSON file, the sanitizer belongs in `quota_lines`, not
only in `detect`.
**Fix:** Collapse whitespace where the value is used (and in `_runner_command`):
```python
command = " ".join((runner.get("command") or "").split())
```
Same treatment is advisable for `detect["jev"]["reason"]` (already collapsed) and the
`candidate_skills` merged from the detect file, which skip the `SKILL_NAME_RE` check that
`answers["skills"]` gets (`goal_prompt.py:523-525`).

### WR-03: A `--flag`-like token in the runner command or objective makes OpenGSD render fail with an opaque error

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:229-230` (guard);
`gp_sections.py:316` (source)
**Issue:** `_inline_problems` rejects any `--[A-Za-z]` token after line 1 of an autonomous block
(D-12). `Runner: {command}` and the user's `objective` are rendered into that block verbatim, so
`cross_ai_command: "node .planning/scripts/cross-ai.mjs --cli x"` (or an objective such as "remove
the --force option") makes every OpenGSD render exit 2 with only
`flag-like token after line 1 of the block`. Reproduced. The message names neither the line nor the
field, and SKILL.md gives the agent no remedy (it says to "relay the message, fix the input").
**Fix:** Either neutralize the token where it is written (for example render the runner as
`node .planning/scripts/cross-ai.mjs` plus "with its configured flags", or insert a zero-cost
rewrite such as `-‑flag`), or make the guard message name the offending line's section:
`f"flag-like token in {section}: {line[:40]}..."`. Add a test for a flagged runner command.

### WR-04: `OSError` during write escapes as a traceback and exit 1

**File:** `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:562-578`;
`gp_render.py:413-427`
**Issue:** `main` catches `UsageError`, `GuardError`, `AttributeError`, `KeyError`, `TypeError`,
`ValueError` but not `OSError`. A read-only or missing-permission output directory raises
`PermissionError` from `tempfile.mkstemp`/`os.makedirs`; reproduced (`output_dir: "ro"` with mode
555) giving a Python traceback and exit code 1. The documented contract (module docstring,
`EXIT_CODES_EPILOG`, SKILL.md) is "0 ok, 2 with a JSON error on stderr".
**Fix:** Catch `OSError` in `main` and print `{"error": "cannot write the goal file"}` (no path,
per the no-echo convention) with exit 2; add a CLI test using a read-only directory.

### WR-05: A dependency cycle among superpowers plans is reported as a roadmap error and blocks unrelated plan selections

**File:** `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:345-350`;
`gp_scope.py:263` (`execution_order(plans)` over all plans)
**Issue:** `detect_scope` orders every plan in `docs/superpowers/plans` even when the work set names
a subset, and `_scope` converts the resulting `ValueError("dependency cycle ...")` into
"the roadmap lacks a phase named in --work-set or has a bad shape". Reproduced in a repo with no
roadmap: plans `a.md` and `b.md` depending on each other make `detect` fail, and so does
`--work-set plans:c.md` for an acyclic, unrelated `c.md`. The message points the user at the wrong
artifact and the unrelated-plan case is a false refusal.
**Fix:** Order only the plans the work set selects (move the `_restrict_plans` filter before
`execution_order`, or pass the file names into `detect_scope`), and raise a dedicated error whose
message names the cycle: `UsageError("plan dependency cycle: " + str(exc))`. Add tests for both.

### WR-06: Many or long plan titles push the `/goal` condition over the 1,800 budget and the advised remedy cannot fix it

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:187-194,470-473`;
`SKILL.md:111-113`
**Issue:** `objective_text` embeds the whole `scope_desc` (`"14 plans: <every title>"`) uncut in the
`/goal` condition. Reproduced with 14 plans of about 150-character titles:
`render` exits 2 with "/goal condition over the 1800-character budget" and writes nothing, even
though a loop/plain block could still be produced. SKILL.md tells the agent to "shorten
`objective` and render again", but `objective` is not the cause (the scope description is), so the
agent cannot recover.
**Fix:** Build the condition's scope clause from file names (or cap the title list with the
`fit_line` ellipsis and "see Rails ORDER") so it stays well under the budget, or drop the `goal`
strategy into `dropped` with a reason instead of failing the whole render. Update the SKILL.md
sentence to say the plan list is the usual cause.

## Info

### IN-01: Written goal files get mode 0600

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:420-424`
**Issue:** `mkstemp` creates the temp file with 0600 and `os.replace` keeps it, so the committable
goal file is owner-only (observed `-rw-------`). Git ignores it, but editors/CI users on a shared
checkout see a surprise.
**Fix:** `os.chmod(tmp_path, 0o644 & ~umask)` before `os.replace`, or `os.fchmod(fd, 0o644)`.

### IN-02: `write_atomic` exists-check is racy

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:413-427`
**Issue:** "never overwrites" relies on `os.path.exists` followed by `os.replace`, which overwrites a
file created in between. Low likelihood in a solo-dev tool.
**Fix:** Publish with `os.link(tmp_path, target)` (fails with `FileExistsError`) then unlink the temp.

### IN-03: A nonexistent `--repo` is accepted silently by `detect`

**File:** `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:438-452`
**Issue:** `detect --repo tmp/rv/nope` exits 0 with scope `none`; a typo yields a plausible-looking
empty result instead of an error.
**Fix:** `if not os.path.isdir(args.repo): raise UsageError("--repo is not a directory")`.

### IN-04: Wrong error text for an empty phase list

**File:** `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:171-175,209-213`
**Issue:** `_phase_numbers` reuses `_names`, so `--work-set phases:,` reports "--work-set names no
plan files".
**Fix:** Pass the noun into `_names` or raise a phase-specific message.

### IN-05: Tests hardcode an absolute machine-style path and miss the cases above

**File:** `tests/goal_prompt_fixtures.py:15`; `tests/test_ai_kit_spec_goal_prompt_common.py:27,160`
**Issue:** `FAKE_HOME = "/var/home/fakeuser"` is an absolute path literal (AGENTS.md: never hardcode
an absolute path in tests). It is only a string for the guard, but it can be derived
(`os.path.join(tempfile.gettempdir(), "fakeuser")`). More importantly no test covers a gapped
phase list, an absolute `--out-dir`, a multi-line or flagged runner command, `OSError` on write, or a
plan cycle (see CR-02, WR-01 to WR-05).
**Fix:** Derive the fake home from `tempfile.gettempdir()` and add the missing cases.

### IN-06: Missing blank lines after class bodies

**File:** `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:72-73`;
`skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py:22-24`
**Issue:** A module constant follows a class body with zero or one blank line (PEP 8 E305). Ruff's
selected rule set does not flag it, so it stays unnoticed.
**Fix:** Two blank lines after each class.

## Dispositions

Every Critical and Warning was re-verified against the code (CR-01 reproduced again: `PWNED`
was created by `detect`) before fixing; each fix has a test that fails on the old code.

- CR-01: fixed in 2b7d55e. `detect` probes only `node <path>/cross-ai.mjs`; any other shape is
  "usability unverified" and never executed.
- CR-02: fixed in 6ac2d78. `detect` now reports `scope.roadmap_order`; `render` refuses a phase
  set that is not a contiguous roadmap run (the check is skipped when the key is absent).
- WR-01: fixed in 625fc5e (absolute or `~` `--out-dir` is refused, same as `..`).
- WR-02: fixed in b87cca6 (whitespace collapsed in `quota_lines` and `_runner_command`).
- WR-03: fixed in b87cca6 as a message fix. The guard itself is intentional (D-12); the refusal
  now names the section holding the token.
- WR-04: fixed in 625fc5e (`OSError` gives a JSON error, exit 2).
- WR-05: fixed in 7e34979 (only the selected plans are ordered; a cycle is reported as such).
- WR-06: fixed in b87cca6 (the `/goal` scope clause is cut at `GOAL_SCOPE_CAP` = 600 characters,
  so the SKILL.md advice to shorten `objective` is now accurate).
- IN-03: fixed in 625fc5e. IN-04: fixed in 625fc5e. IN-05: fixed in 7e34979 (fake home derived
  from the temp dir; the missing cases are covered by the new tests). IN-06: fixed in 7e34979.
- IN-01 (mode 0600): deferred; git ignores the mode bits and the owner-only file is harmless.
- IN-02 (exists-check race): deferred; a single-user tool, and `os.link` publishing is not
  portable to every filesystem.

Follow-up c794ce9 narrows a type for pyright.

---

_Reviewed: 2026-10-31T16:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
