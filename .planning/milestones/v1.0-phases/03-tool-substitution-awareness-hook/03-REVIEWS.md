---
phase: 3
reviewers: [opencode]
reviewed_at: 2026-09-09T23:23:00Z
plans_reviewed: [03-01-PLAN.md, 03-02-PLAN.md]
models:
  opencode: "router-env/my-plan-review (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 3

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll verify the plans' claims against the actual repo before writing the review.
# Cross-AI Plan Review — Phase 03 (Cycle 3 of 3, final)

Verified against live source: `tools/setup.py` (all cited line ranges), `pyproject.toml`, `.pre-commit-config.yaml`, `Makefile`, `tests/test_setup.py`, `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py`, `README.md`, and the live machine state (`rtk 0.44.1` output, `~/.claude/settings.json`, `~/.cursor/hooks.json`, `gsd-cursor-session-start.js`). Every load-bearing factual claim I checked resolved true except the two findings below.

**Convergence verdict up front:** the cycle-2 MEDIUM (non-dict array elements crashing the wiring/unwiring) is **correctly and completely fixed** by `_hook_entries_shape_ok` + `_load_hook_config(nested=...)`, and all seven cycle-2 LOW items landed. I found **zero HIGH/blocking** findings and **two new MEDIUM** findings (one shared by both plans, one plan-01-specific). Since this is the final cycle, both are non-blocking but both should be corrected in plan text before execution — one is a false live-verified claim (this project's core-value class of error) and one is a test that fails as literally specified.

---

## 03-01

### Summary

A mature, unusually well-evidenced plan. Every structural claim I traced against the repo is accurate: `_read_json`'s three-way `{}` conflation (tools/setup.py:1320-1329), `_write_json`'s non-atomicity (tools/setup.py:1332-1337), `unwire_statusline`'s substring discipline (tools/setup.py:1415-1433), `launch_wizard`'s function-scoped `import wizard_app` at tools/setup.py:2182 (the round-2 E402 correction is exactly right — ruff's `files:` regex covers `tools/` and per-file-ignores exempts only `tests/*`, pyproject.toml:42-46), the py-compile regex gap (.pre-commit-config.yaml:48 vs the ruff regex at :21), pyright's include list (pyproject.toml:93), the wizard-commit test harness (tests/test_setup.py:2157+), and the live machine state (3 `SessionStart` entries all lacking `matcher`; rtk's `PreToolUse` entry at index 9 of 10; `rtk init --show` output verbatim). The cycle-2 fixes are correctly integrated. Two residual issues, below.

### Strengths

- **Cycle-2 MEDIUM completely fixed.** `_hook_entries_shape_ok(entries, nested)` validates every array element and, when `nested=True`, every member of each entry's inner `hooks` list, routed through `_load_hook_config` so all four walkers (2 wire + 2 unwire, both plans) inherit it by construction. The refusal-not-copy-through choice (notes 15) is coherent with the existing foreign-shape aborts, and both new tests assert the observable refusal (False return + stderr warning + byte-identity) rather than just "no exception". The `nested=True`/false split per host is pinned by tests in both directions — the exact hole round 2 found is closed.
- **All cycle-2 LOW items landed**: function-scoped import (with the corrected precedent citation and a dedicated ruff verify + `test_hook_scripts_need_no_lint_suppression`), bounded stdin drain loop (the single-`select`-then-unbounded-read flaw is correctly diagnosed; worst case is now ~0.5s of silence plus ≤16×64KiB reads), explicit `0o644` create-mode decision, the Claude-dir gate, the `RTK_SIGNAL_NOT_REGISTERED` compose bullet, the per-host labelling of the bare-`{}` claim, and the T-03-07→T-03-11 citation fix.
- Registration is *proven*, not assumed: `TestGateRegistration` text-parses the actual gate configs, and the `pre-commit run py-compile --files` verify's `fails_when` treats "Skipped" as failure — the right paranoia given pre-commit's silent pass-over behavior, including the `git add`-before-`--files` subtlety.
- The atomic-write failure contract is executed (`os.replace` patched to raise → byte-identity + no stray temp file), matching `atomic_write.py:59-62`'s unlink-then-re-raise shape being adapted, not imported (correct layering call, tools/setup.py note 4).
- Honest-sourcing discipline throughout: probe output never interpolated into the message, `created` from an explicit `isfile` not an empty-read inference, degraded states pinned by tests.

### Concerns

- **MEDIUM — notes 13's factual premise is false on this machine: both hosts' config files are `0o600`, not `0o644`.** Verified live: `~/.claude/settings.json` and `~/.cursor/hooks.json` are both mode `0o600`. The note asserts "`0o644` is the mode both hosts' own config files carry today, so a file ai-kit creates is indistinguishable from one the host would have created" — that is a live-verified-sounding claim that is verifiably wrong, which is precisely the PROJECT.md certainty-rule violation class this phase exists to enforce on others. The *consequence*: an ai-kit-created `settings.json` (which can carry `env` blocks and API keys) lands world-readable where the host's own convention on this machine is owner-only. It is pinned by `test_created_settings_file_is_mode_0644` and a must_have truth, so an autonomous executor — forbidden from deviating — will ship it. Not blocking (nothing corrupts; the existing-target branch still copies the real mode), but the decision should be re-taken against the corrected observation (0o600 is the defensible create mode, matching the observed host convention) and the note's rationale rewritten.
- **MEDIUM — `test_wizard_commit_wires_the_hook` as literally specified will fail, and its supporting rationale sentence is false for the empty-selection case.** The plan claims "In the wizard flow this gate never fires: `apply_selection(...)` has already created `~/.claude` by the time the commit closure reaches the wire call." Traced: `apply_selection` (tools/setup.py:1292) only creates directories inside `link_one` (makedirs at the symlink site), and the specified test invokes `commit(setup.Selection([]), {"adopt": False})` with `entries = {cat: [] ...}` — nothing is linked, `~/.claude` is never created, and the round-2 T-03-18 dir gate then correctly returns False creating nothing, so the assertion "the scratch `settings.json` now carries exactly one ai-kit entry" fails. The round-1 F4 test and the round-2 T-03-18 gate were added in different rounds and were never reconciled. Fix is one line — the fixture must pre-create the scratch claude dir (or pass a non-empty selection so `link_one` makedirs it) — but the plan's no-deviation format means the executor hits a red test with no sanctioned resolution. Same gap applies to `test_wizard_abort_leaves_settings_untouched`, which snapshots a `settings.json` the fixture must first create.
- **LOW — SC-3 "never perceptibly delays" vs a 2.0s probe bound.** A machine where `rtk` resolves but hangs costs up to 2.0s (probe) + up to 0.5s (stdin drain) ≈ 2.5s before context injection. Arguably perceptible; RESEARCH's own guidance said "a few seconds at most," so this is consistent with research but in tension with the roadmap's wording. Acceptable if deliberate; worth a one-line note.
- **LOW — `main()`'s fallback can itself raise.** If the initial `emit` fails because stdout is closed/broken, the `except` handler writes `{}` to the same broken stdout. Truly an edge (a broken pipe kills the hook either way, and Claude Code treats hook failure as non-blocking), but "never writes a traceback, never exits non-zero" is stated absolutely.

### Suggestions

- Amend notes 13 and the must_have/test to `0o600` (or explicitly record the corrected observation and re-justify `0o644` as a deliberate divergence from the host's observed mode — but then the note must say it diverges, not that it matches).
- Add one sentence to Task 1's `test_wizard_commit_wires_the_hook` spec: "pre-create the scratch `claude_dir` (e.g. `os.makedirs(paths.claude_dir)`) — `apply_selection` with an empty selection creates nothing (tools/setup.py `link_one` only makedirs at link time), so without it the T-03-18 dir gate correctly refuses and the test fails." Same for the abort test's fixture.
- Optionally record the accepted worst-case start delay (~2.5s) against SC-3, or drop `RTK_PROBE_TIMEOUT_SECONDS` to ~1.0s.

### Risk Assessment

**MEDIUM (non-blocking).** The architecture, safety contracts, and gate registrations are verified-correct against the repo; the cycle-2 fix is complete. The two MEDIUMs are a wrong factual premise pinned by a test (mode) and a fixture/spec inconsistency that produces one red test — both one-line corrections to plan text, neither a corruption or crash risk if left unaddressed (the mode issue is a mild permission loosening on fresh machines only; the test issue surfaces immediately and loudly during execution, not silently).

---

## 03-02

### Summary

A well-scoped closing plan that correctly reuses plan 01's primitives rather than re-implementing them, with the Cursor-side schema differences (lowercase `sessionStart`, flat array, `version` top-level key) all verified against the live `~/.cursor/hooks.json` (top-level keys `['hooks', 'version']`; GSD's flat entry with `gsd-managed`; `rtk hook cursor` present in `preToolUse`). The `nested=false` vs `nested=True` discipline per host is pinned by tests in both failure directions; the uninstall symmetry (D-10) is closed with byte-identity no-op guarantees; the `version`-on-create rule correctly depends on `_load_hook_config`'s `created` flag. It inherits plan 01's `0o644` create-mode issue and has one minor dependency-fragility point.

### Strengths

- **Correct reuse discipline**: `wire_hook_cursor`/`unwire_hook_*` route every read through plan 01's `_load_hook_config` with the per-host `nested` flag, which is simultaneously the anti-clobber guard, the element-crash guard, the `created` source for the `version` rule, and the pylint-budget mechanism — one helper, four jobs, all traced to real constraints (pyproject.toml:66-71).
- The round-2 split between "no `hooks` key → walked and kept" and "`hooks` present but not a list of dicts → refused before the walk" (notes 11) is the correct repair of round 1's unachievable wording — iterating a string yields characters and `.get` on a character raises, so refusal a level earlier is the only sound design.
- `test_both_hosts_carry_the_same_message` mechanically pins D-09/Pattern 1 — divergence between the two envelopes cannot be introduced silently.
- The human-check for uz (real-machine smoke test, explicitly forbidden to the executor per Rule 5) and the Rule 7 docker/podman circuit-breaker are both present; podman verified available on this machine.
- README insertion points verified: `## Other tools` at README.md:399, `## Layout` tree at README.md:414 — both exist as described.

### Concerns

- **MEDIUM (inherited) — the `0o644` create-mode decision applies here too.** On a machine where `~/.cursor/` exists but `hooks.json` does not, ai-kit's `_atomic_write_json` creates it at `0o644` while the observed live file is `0o600` (verified this session). Same fix as plan 01; nothing additional in this plan's own text is wrong about it.
- **LOW — wave-2 execution depends on plan 01's exact symbol surface.** Task 1's `<read_first>` says "read plan 01's `_load_hook_config` ... AND its `nested` parameter" — good — but the plan also hard-codes plan-01 symbol names and semantics (`created` flag, `_hook_entries_shape_ok` behavior) in ~10 places. If plan 01's executor renames anything, this plan's tasks misfire. The dependency is declared (`depends_on: ["03-01"]`) and the read-first mitigates it; this is normal plan-chaining risk, noted for the orchestrator.
- **LOW — Cursor `command`-string claim verified only by analogy for the `.py` case.** The live entries are a node-resolution string, a compiled binary, and an `sh` conditional — none is a bare `python3 -S <file>` invocation. A1's promotion to "verified" is fair *because* Task 1's end-to-end subprocess test executes the stored string exactly as written, but the promotion happens at test time, not before — the plan says this correctly; just flagging that if Cursor's hook runner mishandles a non-JS target in some subtle way (e.g., PATH resolution of `python3` inside Cursor's environment), the fallback is undocumented. The failure mode is loud (no briefing injected) and covered by uz's human-check smoke test, so LOW.

### Suggestions

- Inherit whatever create-mode decision plan 01 lands on (preferably `0o600` per the corrected observation); no plan-02-specific text change needed beyond that.
- Consider one sentence in Task 1 noting the fallback if Cursor's runner refuses a Python `command` target (wire the same message through a tiny `sh -c 'python3 -S …'` wrapper or document the gap) — or explicitly accept that the human-check is the only detection path.

### Risk Assessment

**LOW-MEDIUM (non-blocking).** This plan's own content is verified-correct against live state; its only MEDIUM is inherited from plan 01's mode decision, and its residual risks are declared, tested, or routed to uz's human-check. The phase-closing gates (`make test`/`lint`/`validate`/`e2e-docker`) are the right final evidence, and the clean-room run is precisely where any PATH-leak in the new suite would surface.

---

## Cross-Plan & Final Verdict

- **Cycle-2 MEDIUM (non-dict array elements → `AttributeError` out of the commit closure / `cmd_uninstall`): FIXED, completely.** The central `_hook_entries_shape_ok` validator, the `nested` flag per host, the refusal-with-warning-and-byte-identity behavior, and executed tests on both hosts and both paths close the crash surface with no walk-site guards left to forget.
- **Cycle-2 LOW items: all addressed** (E402, bounded drain, mode decision, dir gate, compose bullet, `{}` labelling, threat-ID typo). Two of the fixes introduced the two new MEDIUMs above — the dir gate broke an existing test's assumptions, and the mode decision was taken on a false premise.
- **Remaining findings: 0 HIGH, 2 MEDIUM, 4 LOW — all non-blocking.** Both MEDIUMs are one-line plan-text corrections (create-mode `0o600`; pre-create the scratch `claude_dir` in the F4 test fixtures). Since convergence stops after this cycle, I recommend the planner applies those two edits directly (they are within the plans' own locked scope — no requirement, architecture, or task-boundary change) and the phase proceeds to execution. Neither finding, if unaddressed, corrupts a config, crashes an install silently, or leaves a gate decorative: the test failure is loud and immediate, and the mode loosening is bounded to ai-kit-created files on fresh machines.

**Overall risk: MEDIUM, trending LOW after the two one-line edits.** The plans are exceptionally well-grounded — nearly every cited line number, regex, threshold, and live-state claim I checked resolved exactly as written, which is rare — and they achieve the phase goals as scoped.

---

## Consensus Summary

Single-reviewer cycle (opencode only). No cross-reviewer consensus synthesis applies. The reviewer's own cross-plan verdict is captured above under "Cross-Plan & Final Verdict."

### Agreed Strengths
N/A — single reviewer this cycle.

### Agreed Concerns
N/A — single reviewer this cycle.

### Divergent Views
N/A — single reviewer this cycle.
