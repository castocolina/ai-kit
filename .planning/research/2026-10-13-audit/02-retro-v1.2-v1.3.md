# 02 — v1.2 and v1.3 so far: what was promised and what was delivered, plus the backlog and todos

- **Date:** 2026-10-13
- **Trees examined:**
  - Review tree `review-v13` at `0acbd06` (tip of `gsd/v1.3-curated-config-v2`).
  - `main` at `de7dcbb`.
  - Side branches and worktrees from `git worktree list`.
- **Method:** read-only. I re-ran the locked toolchain against the review tree:
  - `ruff 0.15.18` and `pyright 1.1.410`, both from the base checkout's `.venv`, which matches `uv.lock`;
  - the stdlib unittest suites, with `PYTHONDONTWRITEBYTECODE=1`.
  
  I made no live AI-CLI calls apart from `detect-current-runtime`, which only reads the environment.
- **Confidence labels:**
  - **[V]** verified by a command or file read cited here.
  - **[I]** inference.
  - **[I-low]** weak inference.

---

## 0. Ranked top findings

1. **[V] Git hooks never run, in any commit, on either branch.**
   - `.git/config` sets `core.hookspath = /home/user-zero/git/personal/ai-kit/.git/hooks`. That directory does not exist (`ls` returns ENOENT), so git silently skips every hook.
   - The 16-06 SUMMARY gives a different root cause: "`.git/hooks/pre-commit` points to a missing venv". That diagnosis is wrong. The script in `.git/hooks/pre-commit` would fall back to `~/.local/bin/pre-commit`, which exists, but git never reads that directory.
   - No pre-push hook is installed either, so the pyright, vulture and unittest pre-push stages never ran on a push.
2. **[V] Nothing from v1.3 is off this machine.**
   - `main` is 283 commits ahead of `origin/main` and 629 ahead of `gitlab/main`.
   - `gsd/v1.3-curated-config-v2` (343 commits beyond `origin/main`), `spec/host-split-statusline`, `poc/cursor-statusline` and `backup/gap-coloring-52def0f` are on no remote. `git branch -r --contains` returns nothing.
   - The 16-HANDOFF addendum advised a push, but it was never done.
3. **[V] Phase 16 delivered its code, but the phase is not closed.**
   - There is no `16-VERIFICATION.md`.
   - `16-VALIDATION.md` is still `status: draft`, with every row at "⬜ pending" and approval pending.
   - `STATE.md` says `status: verifying`, `stopped_at: Phase 20 context gathered` and `percent: 0`.
   - `REQUIREMENTS.md` still shows SPEC-01..04 as unchecked and "Pending".
   - `ROADMAP.md:67` still shows Phase 16 as `[ ]`.
   - The manual live verifications that Phase 16 promised never happened. The real cache `~/.cache/ai-kit/spec/runtimes.json` has no `schema_version`, and `model-catalog.json` does not exist.
4. **[V] The status line the user actually runs is the v1.2 code.**
   - `~/.claude/settings.json` runs `python3 -S ~/git/personal/ai-kit/tools/status-line.py`, which is the base checkout on `main`.
   - Every `~/.claude/skills/ai-kit-*` entry is a symlink into that same checkout.
   - As a result, none of the gap-coloring commits and none of the Phase 16 detection or enumeration changes are live for the user.
5. **[V] The host environment that v1.3 Phases 20–22 assume no longer exists.**
   - Only `~/.claude/gsd-core` exists, and it is at **1.16.0**.
   - The spec (`design.md:21`) and `20-CONTEXT.md:68,127` assume claude 1.14.0, opencode/codex 1.13.0 and cursor 1.12.0.
   - `~/.config/opencode/{agents,commands}`, `~/.codex/agents` and `~/.cursor/agents` hold zero GSD files. GSD looks uninstalled from every host except claude.
   - `~/.gsd/defaults.json` has `runtime: codex`. INV-03 will therefore flag a "runtime set to another host" conflict on every claude-host inventory.
6. **[V] Three branches define three different "Phase 999.4" entries.**
   - `main` (`de7dcbb`) and `spec/host-split-statusline` (`703b470`): host-split status line.
   - v1.3 (`0acbd06`): ponytail as a recommended skill set.
   - Merging v1.3 into main will produce a ROADMAP conflict and a duplicate phase id. One of the two needs renumbering, for example to 999.5.
7. **[V] The gap-coloring commits (`d23749b..52def0f`) work and are tested, but they are not recorded anywhere in planning.**
   - The code is correct and its tests are green.
   - It deliberately reverses the Phase 8.1 decision, which the user confirmed live, yet `PROJECT.md:199` still records "burn pace … ✓ Good".
   - `v1.2-REQUIREMENTS` REQ-stln-time-relative-color still describes the pace ratio.
   - The spec header still reads "draft, awaiting user review".
8. **[V] `ruff` and `py-compile` do not check the core Phase 16 package.**
   - In `.pre-commit-config.yaml:21,50`, the pattern `skills/ai-kit-spec-review/ai-kit-spec-review` matches no file. The real entry point is `ai-kit-spec.py`.
   - As a result, none of the 21 files in `ai_kit_spec/` are linted at commit time. One SIM105 is open there today.
9. **[V] The v1.2 cross-milestone lint debt is still open, unchanged.**
   - 12 ruff findings in the gated scope (status-line.py 6, wizard_app.py 2, test_ai_kit_spec_superpowers.py 4).
   - 6 pylint findings.
   - So `make validate` cannot pass on either branch. The Retrospective lesson "fix lint debt in its own quick task" was not acted on, and the debt was deferred once more in 16-HANDOFF.
10. **[V] Two internal contradictions in the v1.3 planning docs.**
    - `REQUIREMENTS.md:77` (Out of Scope) says "missing skills are explained and offered only". `SKL-03` (`:46`) and 18 D-03 say "silently omitted".
    - `REQUIREMENTS.md:6` calls the spec "approved", but the spec header (`design.md:4`) still says "draft, awaiting user review".

---

## 1. v1.2: what was promised and what was delivered

### 1.1 Requirements (7/7)

**[V]** Status: **delivered**. The audit (`v1.2-MILESTONE-AUDIT.md`) cross-checked 7/7 REQ-rules-*.

On the v1.3 tip I re-ran the rules suites and usage-metrics:

```
python3 -m unittest tests.test_ai_kit_rules_common … tests.test_ai_kit_project_rules_all tests.test_ai_kit_usage_metrics
Ran 970 tests … OK (skipped=1)
```

No regression from v1.3 work.

### 1.2 Tech debt from the audit, item by item

| # | Audit item | Status at the v1.3 tip | Evidence |
|---|---|---|---|
| 1 | pyright `pair_checks.py:178` | **delivered** (closed by 15.2) | `pyright --pythonpath …` prints `0 errors, 0 warnings`; `tool_catalog.py:383 class PairRow(TypedDict)` |
| 2 | Phase 15 hand-off not live-exercised | **accepted, still not live** | Audit "Accepted (not debt)"; nothing new |
| 3 | 15.1 WR-01 flat-mode sort guard | **delivered** (15.2, `a3c2df2`) | `dashboard.py:1825 FLAT_SORT_KEYS`, `:1852 flatKey` |
| 4 | 15.1 WR-02 regression test | **delivered** | 18 `*_via_node` tests in `tests/test_ai_kit_usage_metrics.py` |
| 5 | ruff E501/UP031 in usage-metrics tests | **delivered**. Phase 16 briefly regressed it, then fixed it | Clean at `333cf04`; I001 at `b407f8f`; clean again at `99ccb98` (piped ruff) |
| 6 | `cmd_dashboard` has no `--no-open` | **accepted** (D-17) | Unchanged |
| 7 | Cross-milestone lint (status-line, wizard_app, superpowers tests) | **not delivered** (open) | Locked ruff in the gated scope: 12 errors, the same set as `main` (`git show main:… \| ruff --stdin-filename`). pylint: the same 6 (5×C0301, 1×R0914). R0914 went from 16 to 17 locals because of the gap commit `3ac0ae4` |
| 8 | mmdc real-render test fails | **delivered** (by an environment fix, not by code) | `python3 -m unittest tests.test_markdown_to_pdf.TestRenderRealMmdc` → `OK` |
| 9 | 3 pending todos to completed | **delivered** (15.2 `0aa965b`) | `.planning/todos/completed/` holds 3 files |
| 10 | Nyquist: validate-phase never ran for v1.2 | **not delivered** (coverage TODO) | Only `15.1-VALIDATION.md` exists, and it is `status: planned` |

### 1.3 The Retrospective lessons, checked against what v1.3 did

- **"Close milestones on time".**
  - **[V]** v1.2 was closed properly: archives exist and STATE on `main` is `milestone_complete`.
  - **[I]** v1.3 is drifting into the same pattern. The handoff has been reused for unrelated work (the statusline addendum), and backlog items are being appended to the live roadmap on side branches.
- **"Fix lint debt in its own quick task".** **[V]** Not done. It was deferred again in `16-HANDOFF.md` §Deferred Items and in the 16-06 SUMMARY.
- **"Compute the fingerprint deterministically".** **[V]** Phase 16 never reached the verifier, so there is no fingerprint at all.

---

## 2. v1.3 Phase 16: plan by plan

**Test evidence on the tip.**
- **[V]** `python3 -m unittest tests.test_ai_kit_spec tests.test_status_line tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_spec_gsd tests.test_ai_kit_opencode_providers tests.test_arch` → `Ran 1150 tests … OK`.
- **[V]** Every test class named in `16-VALIDATION.md`'s per-task map exists in `tests/test_ai_kit_spec.py`; I grep'd for 15 classes and none were missing.

### 16-01: codex enumeration (SPEC-02, SPEC-03 / D-05, D-07, D-08). **Delivered [V]**
- `detection.py:201 detect_codex_models` runs `[binary, "debug", "models"]` as an argv list (`:216`).
- The fixture `tests/fixtures/codex_debug_models.json` exists.
- The live cache, written by the `main` code, has `codex` models=0. So codex enumeration has never run against the real cache. That gap is item 3 under §4.

### 16-02: pi/codex host detection (SPEC-01 / D-01..D-03). **Delivered [V]**, with live confirmation still pending
- `_RUNTIME_ENV_SIGNALS` (`detection.py:50-57`) is pi, opencode, cursor, codex (THREAD_ID, VERSION), then claude.
- `pi` is in `_VALID_NATIVE_RUNTIME` in both `model_catalog.py:53` and `config_io.py:100`.
- Live run from this session: `{"native_runtime": "claude"}`, with only `CLAUDECODE` set.
- The codex signal is still "not live-verified". That check is assigned to Phase 20 (D-05).

### 16-03: `schema_version` (D-12). **Delivered in code [V]**, with no live effect yet
- `RUNTIMES_SCHEMA_VERSION = 2` (`detection.py:15`) and `CATALOG_SCHEMA_VERSION = 2` (`model_catalog.py:15`), stored in `_meta`.
- **[I]** The `main` code writes to the same cache path without `schema_version`. So until v1.3 merges, every v1.3 `--if-stale` run will treat a cache written by `main` as stale, and the two versions will keep overwriting each other. This is harmless but wasteful.

### 16-04: claude aliases, catalog ids and the dated fallback. **Delivered [V]**
- `CLAUDE_MODEL_ALIASES` and `CLAUDE_FALLBACK_MODEL_IDS` are dated `2026-09-23` (`detection.py:25-34`). Claude is never executed.
- The "live claude convergence" check in VALIDATION Manual-Only never ran, because no `model-catalog.json` exists.

### 16-05: `image_input` and `image_input_source`. **Delivered [V]**
- `_FIELD_TYPES` has `image_input: bool` and `image_input_source: str` (`model_catalog.py:31-33`).
- The fixture `opencode_models_verbose.txt` exists.
- This plan was executed by native Haiku, not by the cross-AI router (handoff).

### 16-06: ranker purposes, the mechanical floor and the gate. **Delivered [V]**, but the gate is only partly trustworthy
- `PURPOSE_ALIASES` (`model_ranker.py:19`); `ranking-weights.toml` sections `[review] [execution] [planning] [general] [mechanical] [mechanical.floor] coding_index = 35`.
- **The gate verdict.** The executor reported `GATE NOT PASSED`. The orchestrator re-ran it and declared `GATE PASSED`, saying that remaining ruff findings in `tests/test_ai_kit_usage_metrics.py` were "present at base".
  - **[V] That claim is false.** The file is ruff-clean at base `333cf04` and shows I001 at `b407f8f`. It was also listed in PHASE_FILES.
  - Code review caught it later (WR-01, fixed in `99ccb98`), so nothing is broken now.
  - **[I]** The triage step at the gate cannot be trusted without spot checks.
- **[I] A design risk that carries into Phase 17.**
  - All AA scores (`intelligence_index`, `coding_index`, `agentic_index`) come only from Artificial Analysis (`cli.py:231`, `model_sources.py:14`). I did not verify whether a key is available: it is absent from the environment, and I was blocked from reading the secrets file.
  - Without a key, the `mechanical` purpose returns an empty ranking (spec Errata, Ranker).
  - The `planning`, `general` and `execution` purposes would then score every model at `_MISSING_AXIS_DEFAULT = 49`, so only price and context separate them. The planning slot would effectively go to the cheapest model.
  - The spec covers only "no catalog". It does not cover "a catalog with no scores".

### Phase-level closing steps from the handoff. **Not delivered [V]**
- `verify_phase_goal` (16-VERIFICATION), the verify:post hooks (nyquist validate-phase, secure-phase) and `phase.complete 16`: none of these exist.

---

## 3. The five statusline commits (`d23749b..52def0f`), outside Phase 16

**Classification:** delivered as code, **superseding** Phase 8.1, but **not recorded** in planning.

**What they do [V].**
- They replace `util_rate_burn_ratio` (pct divided by elapsed fraction) with these helpers:
  - `util_rate_gap` returns the signed `used − elapsed%`, or None when the window is unreliable;
  - `util_gap_color` grades `|gap|` into bands: ≤5 GREEN, below 11 YELLOW, ≤15 ORANGE, above that RED;
  - `util_gap_sign` sets the sign: `+` means at or under pace, `-` means burning faster.
- The sign is gated by `show_reset`, so the terse tier stays byte-identical.
- `[ramp.rate]` is kept only so that existing config still parses.
- Source: `git diff 1ccdc1e 52def0f -- tools/status-line.py`.

**Quality [V].**
- `tests.test_status_line` passes; it is part of the 1150-test run above.
- No ruff or pylint finding is new: the same 6 ruff and 6 pylint findings exist on `main` at shifted line numbers. The only change is that R0914's local count grew from 16 to 17.

**Semantics [V].**
- The spec says so on purpose: "45% elapsed and 15% used is red … That reversal is required" (`2026-10-09-statusline-quota-window-gap-design.md`, worked checks).
- So low usage late in a window is **RED** again. That is exactly the case the 8.1 user report complained about, but this time it is an explicit user decision.

**Bookkeeping gaps [V].**
- The spec is still `Status: draft, awaiting user review` (`:4`), even though it shipped.
- `PROJECT.md:199` Key Decisions still says "burn pace … ✓ Good".
- `v1.2-REQUIREMENTS.md:160` still amends REQ-stln-time-relative-color for the pace formula.
- The commits are merged into the GSD milestone branch, so the v1.3 Phase 16 verification will see them in its diff (handoff addendum, "Scope note").

**Not live [V].** The user's status line runs the copy on `main`, so the change is not visible yet.

**Dependency [I].**
- `spec/host-split-statusline` and `poc/cursor-statusline` both branched from `2b4b45b`, so they already contain the gap code.
- Building 999.4 (host split) on top of `main`, which does not have the gap code, would conflict.
- So either the gap commits reach `main` first (cherry-pick, or a v1.3 merge), or 999.4 has to be built from the v1.3 line.

---

## 4. v1.3 promises already at risk or stale

1. **[V] `STATE.md` is stale and contradicts itself.**
   - `status: verifying` (`:7`), but `stopped_at: Phase 20 context gathered` (`:8`).
   - "Phase complete — ready for verification" (`:34`), but `percent: 0`.
   - `state_head b407f8f` is 8 commits behind the tip.
   - "Pending Todos: None outstanding" (`:240`), although `main` has 2 pending todos.
   - The decision note on EVAL-06 still says "removed-module cleanup" (`:230`), which 18 D-08 superseded.
   - Blockers from Phases 7 and 8 (v1.1, already shipped) are still listed as open.
2. **[V] `REQUIREMENTS.md`: all 33 requirements are unchecked and "Pending"**, including the 4 that Phase 16 delivered. The STATE decision note says "31 requirements", but REQUIREMENTS counts 33.
3. **[V] Phase 16's live checks never ran.**
   - Real cache `runtimes.json`: `schema_version None`; codex models 0; claude models 0 / `models_source None`.
   - `model-catalog.json` is absent.
   - 17-CONTEXT §specifics already expects the "no catalog" path to be the first run.
4. **[V] The ponytail statement in `18-CONTEXT.md:188` is stale.**
   - The file says "`ponytail` does not exist … not mentioned". Ponytail 5.1.0 is installed (`installed_plugins.json` → `ponytail@ponytail 5.1.0`) with 6 skills under `skills/`.
   - D-03 itself ("just add it if it exists") already covers the installed case. Only the §specifics note and spec §7's install-offer text need to change.
   - The plugin also ships `opencode.json`, `pi-extension/`, `gemini-extension.json` and `AGENTS.md`. This goes beyond what 999.4 lists, and is relevant to non-claude hosts.
   - gsd-core 1.16 `init.cjs:3681` confirms that `global:<plugin>:<skill>` works only on claude.
5. **[V] The gsd-core version facts are stale.**
   - The spec's "1.14.0 / 1.13.0 / 1.12.0" is wrong today: claude is 1.16.0, and the other hosts have no install.
   - In 1.16 there are 35 agents (unchanged) and 125 `VALID_CONFIG_KEYS`, up from 120 in 17-CONTEXT.
   - `RUNTIME_PROFILE_MAP` now has a `pi` entry (claude-* ids) as well as qwen, copilot, hermes and kilo. `cursor` is still missing.
   - Every config key the spec relies on still validates under 1.16 (`isValidConfigKey` probe over 38 keys). There are only two misses, both expected: the bare `plan_review_convergence` (the real key is `workflow.plan_review_convergence`) and `model_policy`, which is an object.
   - 18 D-07 ("`config-set null` deletes the key", verified on 1.14) needs re-checking on 1.16.
6. **[V] The Phase 20, 21 and 22 prerequisites are missing.** These phases assume host gsd-core installs and live host sessions (20 D-01, D-03, which cite opencode gsd 1.13.0). GSD agents and commands on opencode, codex and cursor are all empty, so a reinstall is needed before any host smoke test.
7. **[V] Phases 21 and 22 are in the ROADMAP but have no phase directories or CONTEXT.**
   - This is normal for phases that have not been discussed yet.
   - **[I]** It does carry a risk: SPEC-05 (pi enumeration) and SPEC-06 (cursor wrapper) were deferred into them, but no decisions are recorded there yet.
   - **[V]** No pi fixture exists in `tests/fixtures/`.
8. **[V] Cross-AI execution is unreliable.** `router-env/my-coding` failed four different ways during Phase 16 (handoff §Blockers), so plans 16-05 and 16-06 fell back to Haiku. The handoff plans the same lane for Phases 17 onward.
9. **[V] The xai lane is still recorded as billing-blocked** (memory and `077de1f`). Phase 19 scenario B expects 2 reviewer lanes (18 D-01), and those depend on `router-env/my-plan-review` plus a codex lane.

---

## 5. Gaps between the design spec and Phases 17–22

1. **[V] The spec is still a draft** (`design.md:4`), but REQUIREMENTS calls it approved (`:6`).
2. **[V] Missing-skill handling is contradictory.**
   - Spec §7 says to explain and offer. That is superseded by 18 D-03, and the errata records the change.
   - `REQUIREMENTS.md:77` still says "explained and offered only". That line was never amended.
3. **[V] The per-agent skill cap.** Spec §7 sets "max 3". 18 D-04 replaced it with 2/3/5 by rigor. Errata: recorded.
4. **[V] Rigorous uses 2 reviewer lanes** (18 D-01). This is not in spec §6 or the errata. **[I]** It is harmless, since the CONTEXT files are authoritative, but the errata list is incomplete. Also missing from it: 17 D-02..D-08 and 19 D-03..D-07.
5. **[I] The spec's pi and cursor coverage claim is unmet.**
   - Spec §9: "their code paths ship in this milestone covered only by fixture-based unit tests (real CLI output captured 2026-09-23)".
   - Pi enumeration moved to Phase 22, and no pi fixture exists. So Phases 17 and 18 can only test pi through hand-built inventories, and every pi slot will be `needs_choice`.
6. **[I] A catalog without scores is not covered** (§2, 16-06). The spec and 17-CONTEXT handle "no catalog", but not "a catalog with no AA scores". Without scores, the role-score layer reduces to price.
7. **[V] The spec says nothing about a codex or other foreign `runtime` in `~/.gsd/defaults.json`.**
   - Spec §8 says "runtime already set to another host → offer migration", but only for the project config.
   - INV-03 also checks `~/.gsd/defaults.json`, which today contains `runtime: codex`.
   - **[I]** Phase 17 needs to decide whether a global `runtime` counts as a conflict or only as information.

---

## 6. Backlog (999.x) and todos

### 999.1: shared core for the Config Doctor TUI and CLI. **Partial [V]**
- The engine is already decoupled. `tools/config_doctor_checks.py:3` says "Imports nothing from textual"; `textual` is used only by `config_doctor_app.py`.
- The CLI front end has not been built.
- **Relevant:** still. **Depends on:** nothing.

### 999.2: cron for the usage-metrics pipeline. **Not delivered [V]**
- `skills/ai-kit-usage-metrics/SKILL.md:42` explicitly says it is out of scope.
- **Relevant:** still, and low priority. **Depends on:** nothing.

### 999.3: architecture-layer suite. **Superseded, partly [V]**
- Phase 12 delivered the form-only half, and the ROADMAP note says so.
- The layering-enforcement ambition remains a declared known gap.

### 999.4 on `main` and `spec/host-split-statusline`: host-split status line. **Not delivered; spec and POC exist [V]**
- The design and review are only on `spec/host-split-statusline` (`.planning/specs/2026-10-10-host-split-statusline-design{,-REVIEW}.md`).
- The review has **5 HIGH and 1 MEDIUM findings open** (R3-1..R3-6, all `[ ]`).
- The POC is on `poc/cursor-statusline`: 7 commits beyond the spec branch (`6eb9178..c85f945`). It must not be merged as production code (todo).
- **Depends on:**
  - getting the gap-coloring code onto `main` (§3);
  - resolving R3-1..R3-6;
  - untangling the orphan `worktree-context-tools-manager-plan1` (21 unmerged commits, about 4.9k lines, which touch `tools/setup.py` and `tools/wizard_app.py`; host-split also changes setup and the wizard);
  - fixing the 999.4 numbering collision.

### 999.4 on v1.3: ponytail as a recommended skill set. **Not delivered; mostly absorbed by the Phase 18 design [V/I]**
- **[V]** Ponytail is installed (5.1.0).
- **[I]** 18 D-03 plus spec §7 ("token economy (ponytail, …) → planner, executor, code-fixer") already wire it once SKL-01 scans Claude plugin skills.
- What is genuinely new in 999.4:
  - per-command mapping (review/audit → code-reviewer and the auditors; debt → planner or verifier);
  - the question of whether ponytail can be addressed on other hosts. **[V]** It can: the plugin ships manifests for opencode and pi.
- **Recommended action:** fold it into Phase 18, as the entry itself proposes. Renumber it to free up 999.4.

### Todo `2026-10-11-execute-system-one-decision-skill-plan` (major). **Not delivered [V]**
- `~/.claude/skills/jev-fast-decision/SKILL.md` has no `JEV_BACKEND` (0 grep hits) and still describes the Zen-only design.
- The prerequisite is met: a listener exists on `:8010`, and llm-env HEAD is `3e52502` (System One).
- **[V] A hygiene problem:** 82 scratch files under `.planning/docs/system-one-decision-skill/scratchpad/` are tracked on `main`.
- This is outside the v1.3 scope, because it is a global skill. It is independent of every other item.

### Todo `2026-10-12-promote-cursor-statusline-poc-into-999-4` (major). **Not delivered [V]**
- Its first acceptance checkbox ("999.4 promoted off backlog with plans") is open. The specs have not been copied to `main`.
- **[V]** `main`'s `STATE.md` "Pending Todos" lists only the System One todo, not this one.
- **Depends on:** 999.4 (host split) and the items listed under it.

### Other branches and worktrees [V]
- `worktree-agent-af8d0e0c…`: 1 docs-only commit (`ec47392`, a superseded 15.1 halt note). It can be dropped after a cherry-pick decision.
- `worktree-context-tools-manager-plan1`: 21 unmerged commits, untouched since 2026-07-30. **Not tracked in any roadmap, backlog or todo.**
- These have 0 unique commits and can be deleted: `worktree-ai-kit-spec-foundation`, `feat/install-wizard-tui-v2`, `feat/wizard-enter-hint`, `fix/curl-bash-tty-redirect`.
- `fix/8.1-status-line-rate-burn-pace` has 1 commit, but it is patch-equivalent to work already on `main` (`git cherry` shows 0 unmerged).
- `.planning/milestone.lock` is untracked and stale, with a 2026-09-24 timestamp.

---

## 7. Ranked pending work, with dependencies

1. **Fix `core.hooksPath`, then install the pre-commit and pre-push hooks.** This is a user-config change in the repo `.git/config`, so the user must approve it.
   - Depends on: nothing.
   - Unblocks: every item below that commits code. Without it, gates exist only on paper.
2. **Push `main`, `gsd/v1.3-curated-config-v2` and the spec, POC and backup branches** to a remote, with the user's consent.
   - Depends on: nothing. It protects about 2 months of work that currently exists only locally.
3. **Clear the gated lint debt as one quick task:** 12 ruff, 6 pylint and 1 SIM105, plus fix the dead `ai-kit-spec-review/ai-kit-spec-review` pattern in `.pre-commit-config.yaml` so that `ai_kit_spec/` is gated.
   - Depends on: 1, so the hooks enforce it from then on.
   - Unblocks: a green `make validate`, which Phase 18 SC5 and EVAL-06 require.
4. **Close Phase 16.**
   - Run the gsd-verifier to produce `16-VERIFICATION.md` (covering the out-of-scope statusline commits explicitly), then nyquist and secure-phase, then `phase.complete 16`.
   - Tick SPEC-01..04 and refresh STATE.
   - Run the live `detect-runtimes` / `fetch-model-catalog` probes that VALIDATION promised, against a scratch `XDG_CACHE_HOME` so the user cache is left alone.
   - Depends on: 3, optionally, for a clean gate.
5. **Decide where the statusline gap commits belong**, and update `PROJECT.md:199`, the spec status, and REQ-stln.
   - Depends on: nothing.
   - Unblocks: 999.4 (host split), and makes the change visible in the user's live status line.
6. **Fix the 999.4 numbering collision** by renumbering ponytail, or folding it into Phase 18. Reconcile the v1.3 ROADMAP with `main`'s.
   - Depends on: nothing. It must be done before any merge of v1.3 into main.
7. **Refresh the v1.3 planning facts before planning Phase 17:**
   - gsd-core 1.16 (125 keys, the new `pi` map);
   - the global `runtime: codex` conflict;
   - 18-CONTEXT's ponytail note;
   - the REQUIREMENTS Out-of-Scope line;
   - the spec status;
   - a decision on the "catalog with no scores" case and on AA key availability.
   - Depends on: 4.
8. **Phase 17**, then **Phase 18** (with ponytail folded in), then **Phase 19**.
   - Each depends on the one before. Phase 19 needs the claude host only.
   - Risk: the `router-env/my-coding` cross-AI executor is unreliable, so budget for the native fallback.
9. **Phase 20** (codex and opencode live validation).
   - Depends on: 19, plus reinstalling GSD on codex and opencode (**[V]** both are missing now), plus interactive sessions run by the user.
10. **Phases 21 and 22** (cursor and pi live validation).
    - Depends on: 19, plus GSD reinstalled on those hosts. They also carry SPEC-06 and SPEC-05 with no CONTEXT yet.
11. **999.4 (host-split status line).**
    - Depends on: 5, R3-1..R3-6 resolved, and a decision on the `context-tools-manager-plan1` orphan (setup and wizard overlap).
    - The POC todo depends on this item.
12. **The System One todo** (a global skill). Independent; its prerequisite is met.
13. **999.1 (CLI front end)** and **999.2 (cron)**. Independent and low priority.
14. **v1.2 Nyquist validate-phase backfill.** Optional coverage TODO.
15. **Branch cleanup:** delete the 4 empty branches, `agent-af8d0e0c` and `fix/8.1`; decide the fate of `context-tools-manager-plan1`.
    - Depends on: 2 (push first).

---

## 8. What I did not check

- I did not run the full `make test` or `make validate`. I ran the stdlib suites and linters directly.
- I made no live `codex`, `opencode` or `fetch-model-catalog` calls, because this brief did not allow them.
- I could not check whether an Artificial Analysis key exists: reading the secrets file was blocked by the guard.
- I read 16-REVIEWS cycle 3 only in summary.
- I did not re-verify each of the 16-0x PLAN must-have truths one by one beyond the code and tests cited above.
