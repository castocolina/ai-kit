# Retro: promised vs delivered, milestones v1.0 and v1.1

Scope: v1.0 (phases 1.1, 1.2, 2, 3, 4, 5) and v1.1 (phases 6, 7, 8, 8.1), checked against the five v1.0 PRDs, the pre-GSD `000-ai-kit-overhaul-requirements.md` index, the ROADMAP success criteria (SC), the REQ-IDs, and the README/AGENTS claims.

- **Code under test:** review tree `review-v13` at `0acbd06` (branch `gsd/v1.3-curated-config-v2`), referred to below as `R/`.
- **Comparison point:** `main` is cited where it behaves differently, because `main` is the code the live install symlinks (`~/.claude/settings.json:21` points at the base checkout).
- **Labels:** "Verified" means I ran it or read the code. "Inference" means a reasoned conclusion, and carries a confidence level.

## 0. Method and test evidence

Targeted unittest modules, run in the review tree (`PATH=~/.local/bin:$PATH UV_NO_SYNC=1 uv run python -m unittest tests.<m>`). All of them are green.

| Module | Tests | Result |
|---|---|---|
| test_ai_kit_opencode_providers | 73 | OK |
| test_tool_substitution_hook | 73 | OK |
| test_config_doctor | 81 | OK, **6 skipped** (`textual not installed`) |
| test_config_doctor + _pty, run with the base checkout's textual venv | 85 | OK, 0 skipped |
| test_ai_kit_usage_metrics | 156 | OK |
| test_ai_kit_project_rules_agents | 21 | OK |
| test_ai_kit_gsd_curated_config | 94 | OK |
| test_status_line | 304 | OK |
| test_ai_kit_spec | 594 | OK |
| `bash tests/test_install.sh` | 16 | 16 passed |

Live entry-point exercises, all verified and all writing only to scratch dirs:

- `ai-kit-opencode-providers list/remove` against a fixture.
- `claude_session_start.py`, run with rtk present and with rtk absent.
- `ai-kit-spec.py detect-current-runtime`, with four env shapes.
- `ai-kit-gsd-curated-config` with `ensure-project`, `apply-profile`, `apply-critical-agents`, `apply-workflow-defaults`, `detect-execution-candidate` and `detect-claude-md-path`, in a scratch git repo.
- `ai-kit-project-rules-{agents,makefile} check`.
- `classify_loop.run_classification` against a **copy** of the real refined store.

Not run: `make e2e-docker` (it needs a podman build plus network) and any live cross-AI route.

## 1. Item-by-item classification

### v1.0 Phase 1.1 — Autonomous-run infrastructure

- **SC1/SC4, convergence and cross-AI config keys:** delivered.
  - `R/.planning/config.json` has `plan_review_convergence: true`, `cross_ai_execution: true` and `cross_ai_command: "opencode run --model router-env/my-coding"`.
  - The `review.default_reviewers` key is set.
- **SC2, `make e2e-docker`:** delivered, but **not re-verified at HEAD** by me.
  - The target exists (`R/Makefile:127-132`), and so does `tests/e2e/docker/Dockerfile`.
  - v1.2 Phase 9 recorded it as unrunnable due to host memory pressure (`v1.2-phases/09-.../09-VERIFICATION.md:101`).
  - CI does not run it: `R/.gitlab-ci.yml` has only a secret-detection job, even though it declares a `test` stage.
- **SC3, ONESHOT files naming "real, live-verified routes":** delivered, then regressed. Inference, medium confidence.
  - `ONESHOT-RULES.md:85` and `config.json` `review.models.opencode` both name `xai/grok-4.6` as the fallback.
  - User memory `project_opencode_xai_billing_block.md` records that lane as 403 spending-limit blocked since 2026-09-14.
  - I did not re-probe it live.

### v1.0 Phase 1.2 — Multi-CLI runtime foundation

- **REQ-multi-cli-install-single-branch:** delivered.
  - `R/tools/install.sh:107` reads `git clone --single-branch --branch "$REPO_BRANCH" --depth 1`.
  - The `pull --ff-only` (line 100) and tarball (line 97) paths are intact.
  - The test is `tests/test_install.sh:108-121`, and all 16 harness tests pass.
- **REQ-multi-cli-runtime-detection:** **partial on `main`, fixed only on the unmerged v1.3 branch.** Verified.
  - On `main`, `_RUNTIME_ENV_SIGNALS` checks claude first (`main:skills/ai-kit-spec-review/ai_kit_spec/detection.py:27-32`).
  - So a nested session started from Claude Code reports the wrong host. With `{'CLAUDECODE':'1','OPENCODE':'1'}`, `main` returns `claude`; with `CODEX_VERSION` plus `CLAUDECODE`, it also returns `claude`.
  - The branch reorders to pi > opencode > cursor > codex > claude (`R/.../detection.py:50-57`, Phase 16 D-01 / Phase 20 D-02) and returns `opencode`.
  - This means v1.0 SC2's "reliable" claim was never true for the most common nesting, and the fix ships only when v1.3 merges.
  - The `native_runtime` validation lives in `config_io.py:100-135` and `model_catalog.py:53,157-163`. The CLI is `cli.py:883-885`.
- **PRD Phase 2 Task 4 (wire detection into the catalog-build path):** superseded by the 2026-09-09 amendment, which moved native semantics into `review-spec.toml`.
  - The `model_catalog.py` validator has no producer. A grep for `native_runtime` writers in skills and tools finds only `cli.py:884`.
  - This makes the validator dead code (see §5).
- **SC3, wizard labels `native_runtime`:** delivered. `R/skills/ai-kit-spec-config/SKILL.md:75,244-250,281`.
- **REQ-multi-cli-opencode-ui-research:** delivered.
  - `R/docs/research/opencode-sidebar-status-bar-viability.md:59-74` recommends "wait for upstream", with a concrete re-investigation trigger (a PR on #5971 or #23539).
  - Nothing tracks that trigger (see §2).

### v1.0 Phase 2 — Opencode provider management

- **REQ-opencode-provider-list-remove:** delivered. Verified live.
  - `list` prints id, npm and baseURL and never the apiKey.
  - `remove nope` prints "nothing to remove" and exits 0.
  - `remove alpha` on a fixture whose baseURL contains `{x}` removed exactly that entry. The `/* block */` comment, the other provider and the file mode (644) are preserved, and the result parses.
  - Cosmetic: the removed line is left behind as a whitespace-only line.
- **REQ-opencode-provider-cross-reference-check:** delivered.
  - The output names `review-spec.toml: a model=alpha/gpt` and logs a per-source audit trail.
- **PRD scenario "proceeds only after the user confirms (or a required flag)":** not delivered. Low severity.
  - `remove` runs immediately with no confirm step and no `--yes` flag (`remove --help`).
  - `SKILL.md` has no "confirm" instruction.
  - ROADMAP SC4 only requires that the warning never block, so the ROADMAP SC is met.

### v1.0 Phase 3 — Tool-substitution awareness hook

- **REQ-tool-substitution-hook-wiring (Claude and Cursor):** delivered and live.
  - It is wired in the user's `~/.claude/settings.json:21` and `~/.cursor/hooks.json:6`.
  - It runs in about 21 ms with rtk present, and returns `{}` when PATH lacks the tools.
  - The opencode gap is documented in `R/tools/hooks/README.md:20`.
- **REQ-tool-substitution-detection-composition:** delivered, but the REQ text is **stale**.
  - The REQ says detection uses "`registry.toml` `audience`". `03-CONTEXT.md:64-66` found that no such file or field exists, so it was superseded by the curated 5-pair list (`R/tools/hooks/detect.py:23-29`) plus `rtk init --show`.
- **"Single source of truth mirrored by usage-metrics":** partial.
  - `R/skills/ai-kit-usage-metrics/ai_kit_usage_metrics/family.py:8` reads "Ported from tools/hooks/detect.py::CURATED_SUBSTITUTIONS (not imported)".
  - That makes it a hand copy, and no test asserts that the two copies are equal (grep of `tests/`).
  - The two copies are identical today.

### v1.0 Phase 4 — Config Doctor

- **Diagnostic checks and review screen:** delivered.
  - `R/tools/config_doctor_checks.py` has 25 rows (lines 568-1010) across Claude, opencode, Codex and Cursor, plus `rtk-cursor-integration`. That covers all 12 PRD rows.
  - The entry point is `R/tools/setup.py --config-doctor` (`setup.py:2952-2990`, `--help` lines 16-17).
- **Apply flow:** **partial against the PRD.**
  - Only 4 of 25 rows are apply-eligible: `claude-retention`, `claude-sandbox-enabled`, `opencode-share-mode` and `codex-history-persistence` (enumerated from `CONFIG_DOCTOR_ROWS`).
  - PRD Phase 2 Task 2 promised apply for rows #1-4, #6-9 and #11-12. Missing apply: prompt-cache TTL (#2), telemetry (#4), **opencode permissions (#6, security-relevant)**, **codex sandbox_mode (#8, security-relevant)** and rtk-cursor (#12).
  - `04-03-PLAN.md:130-142` explicitly says "Deferred to a later milestone, not this phase". It was never scheduled (see §2).
  - ROADMAP SC4/SC5 are met for the 4 wired rows.
- **PRD "new SKILL.md documenting the full Checks Catalog, skill-judge gated":** superseded by the TUI-only decision (`04-CONTEXT.md:78-93`, D-05/D-06).
  - No skill exists, so non-Claude hosts cannot reach it as a skill.
- **Test fragility:** verified.
  - The 6 tests that pin the core safety SCs (`TestConfirmApplyScreen`, `TestNoBulkApply.test_no_bulk_apply_binding_action_names` and `test_security_relevant_preview_shows_literal_config`) **silently skip** when textual is missing (`R/tests/test_config_doctor.py:1474-1497`).
  - The review tree's `.venv` lacks textual. With a textual-enabled venv, 85/85 pass.

### v1.0 Phase 5 — Usage metrics dashboard

- **Raw capture, refinement pipeline and dashboard:** delivered.
  - The skill dir has `capture_{claude,opencode,codex,cursor,rtk}.py`, `decomposer.py`, `cwd_state.py`, `pricing.py` and `dashboard.py`. The CLI is `{capture|refine|dashboard|classify|run}`, and 156 tests pass.
  - The real store holds 92,520 rows (claude 35,698, opencode 17,435, rtk 31,040, codex 8,306, cursor 41).
  - The store was last refreshed **2026-09-21** (file mtime), consistent with backlog 999.2 (no cron) never being built.
- **REQ-usage-metrics-classification-refinement-loop:** delivered as code, **never exercised on real data**. Verified.
  - The real store has 3,334 opaque rows (3,006 unclassified plus 328 control_flow_script) and **0** `inferred_family` rows.
  - Running `run_classification` on a copy gives `{'groups_found': 243, 'rows_reclassified': 210}`: cat 69, grep 70, ls 65 and sed 6, all LOW confidence.
  - `run` deliberately excludes `classify` (`cli.py:117-121`; `SKILL.md:70` says "never part of `run`").
  - The PRD called the real run a "follow-up action" (PRD lines 445-449). No one owns it.
- **PRD Phase 5 Task 3, deferred axes:** partial.
  - Runtime and duration later appeared (the `runtime` and `exec_duration_ms` columns in `refined_store.py:66-99`).
  - LOC, quota/resource-pressure failures and service_tier were never planned.
- **Cursor `store.db` structured capture:** deferred as "additive future work" (the 2026-09-10 REQ amendment, `git show ea22271:.planning/REQUIREMENTS.md:41`). Never scheduled.

### v1.1 Phase 6 — AGENTS.md rules checker

The skill was renamed and split in v1.2, so its scope now lives in `ai-kit-project-rules-agents` and `-makefile`.

- **REQ-agtmd-workflow-rules:** delivered.
  - `check` on a near-empty fixture reports R01-R17 individually: missing, near_miss or not_applicable. That covers all 13 REQ rules plus R02.
  - Dogfooding on ai-kit's own AGENTS.md returns only R07 as not_applicable, because the worktree has no `.codegraph/`.
- **REQ-agtmd-makefile-rules:** superseded by `ai-kit-project-rules-makefile`. Target-gap detection works: it flags `arch-test`, `e2e-test`, `setup-env`, `test-integration`, `test-unit` and `validate`.
  - **Delivered-then-regressed for the "per-language tool recommendation".** On a python fixture, `formatter`, `security-scanner` and `code-smell-detector` return `recommendation: null, needs_research: true`.
  - The v1.1 research cache was written to `~/.cache/ai-kit/agents-md-rules-checker/stack-refs/python.json` (2026-09-11). The v1.2 rename moved the namespace to `project-rules-makefile` (`stack_cache.py:19-20`) without migrating it, so the cached python recommendations are orphaned.
- **REQ-agtmd-wrapper / skill-pipeline:** delivered. `SKILL.md` wraps `/agent-md-refactor`. I did not re-run skill-judge.

### v1.1 Phase 7 — Curated GSD config v1

- **All 4 REQ-cfg items:** delivered. Verified live.
  - In a scratch repo, the full subcommand chain wrote a config with `model_profile=balanced`, `plan_review_convergence: true`, `cross_ai_execution: true`, a haiku floor (`critical_agents.py:18,39-41`), 10 `effort.agent_overrides: high` entries and a 27-key workflow bundle.
  - Writes go through gsd-tools.
- **Not delivered:** Phase 7's own expectation that ai-kit's `claude_md_path` would update "implicitly once the skill runs on this project" (`07-CONTEXT.md` Deferred section).
  - `R/.planning/config.json` has `claude_md_path: ./CLAUDE.md`, but no `CLAUDE.md` exists in the repo or the base checkout.
  - The skill's own `detect-claude-md-path --project-dir R` returns `./AGENTS.md`.
  - So the skill was never run on ai-kit itself.
- **Ponytail note:** user memory `project_curated_config_v1_untested.md` says the user never tested v1 and judged that it "tried to cover a lot and did little". v1.3 keeps it alongside v2 (Phase 18 D-08).

### v1.1 Phases 8 and 8.1 — Status-line quota color

The formula has changed direction three times in a month:

1. Phase 8: `pct / remaining_fraction`.
2. Phase 8.1: `pct / elapsed_fraction`, a pace ratio.
3. 2026-10-09: absolute gap `|pct - elapsed_pct|`, with a `+`/`-` sign glued to the percentage. This came from a superpowers spec, outside GSD.

Classification:

- **On `main`:** 8.1 is delivered (`main:tools/status-line.py:1492 util_rate_burn_ratio`, `main:tests/test_status_line.py:179 TestRateBurnRatio`).
- **On the review branch:** 8 and 8.1 are **superseded** by the gap coloring.
  - Commits `d23749b`, `3ac0ae4` and `0a46a0c` (2026-10-09) delete the pace helpers and `TestRateBurnRatio`.
  - The replacement code is `R/tools/status-line.py:1492-1534` (`util_rate_gap`, `util_gap_color`, `util_gap_sign`).
- **Phase 8 SC2 and 8.1 SC2 ("color-only; displayed percentage byte-identical"):** **broken by design** in the replacement, because a sign is now prefixed to the number (`docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md:13`).
  - That spec's header still reads "Status: draft, awaiting user review", yet it has shipped.
  - No ROADMAP or REQUIREMENTS entry records the change. It is noted only in `16-HANDOFF.md:207-240`.
- **Phase 8 SC4 ("fed into the unchanged `theme.ramps['rate']`"):** the ramp still exists (`status-line.py:172`) but is unused. It is "kept for config-parse compat only" (`statusline.toml.sample:149-152`).

### Pre-GSD `000-ai-kit-overhaul-requirements.md` (E1-E7)

Spot-checked: delivered.

- E2: `mermaid_style.py`.
- E4a/E4b: `util_parse_color`, plus `[ramp.*]` in the sample config.
- E4c: the external-segment header grammar at `status-line.py:1955`, and `test_external_segments`.
- E6: `skills/markdown-to-pdf`.
- E7 FR-7.3/7.4: the `slowest` segment at `status-line.py:81,128`. The E7 PRD marks both "DECIDED + DONE".

The index status table (lines 8-18) is **stale**: it still says "plan ready", "design ready", "design in progress", "PRD pending" and "open". E5's "plain stdin prompts, zero TUI deps" was superseded by the Textual wizard.

## 2. Lost deferrals (deferred "to later", never scheduled)

Compared against Backlog 999.1-999.4 (`R/.planning/ROADMAP.md:259-360`) and the todos (only two are pending on `main`, both from 2026-10, unrelated).

1. **Config Doctor apply for the remaining rows**, including the two security-relevant ones: opencode permissions and codex sandbox.
   - Source: `04-03-PLAN.md:130-142`, "Deferred to a later milestone".
   - No backlog entry exists. 999.1 covers only the TUI/CLI shared core.
2. **Usage-metrics classify against real data.**
   - Source: PRD lines 445-449, "follow-up action".
   - Never run, so the store has 0 inferred rows; 210 would be reclassified.
3. **Pre-existing lint debt** in `status-line.py`, `wizard_app.py` and `test_ai_kit_spec_superpowers.py`.
   - Deferred in `01.1/deferred-items.md`, `06/deferred-items.md`, `07/deferred-items.md` and the v1.1 audit tech_debt.
   - RETRO lesson 2 says "schedule it once", but no todo or phase exists.
   - It is still present: `ruff` finds 12 errors in the validate scope (6 status-line, 2 wizard_app, 4 test file), and `pylint` finds 6 in `status-line.py`, which is in its hook scope. So `make validate` is still red. This is an inference from hook scopes (`.pre-commit-config.yaml:21,27`); I did not run `make validate` itself.
4. **Nyquist VALIDATION.md** is missing for 10 of 10 v1.0/v1.1 phases (`ls .../*VALIDATION*` finds none). The v1.1 audit flagged it and it was never scheduled.
5. **Installer "offer to install missing uv/textual" UX.** Source: `02-CONTEXT.md` Deferred, which says it "belongs in its own future phase/PRD". Never captured.
6. **The opencode sidebar re-investigation trigger** (research doc lines 71-74). No watch item or todo exists.
7. **Usage-metrics LOC, failures and service_tier axes** (PRD Phase 5 Task 3), and **Cursor `store.db`**. Never scheduled.
8. **ai-kit's own `claude_md_path`**, which Phase 7 said would update "implicitly". It points at a missing file (§1).
9. **No v1.0 milestone audit was ever run.** No `v1.0-MILESTONE-AUDIT.md` exists, and no v1.0 or v1.1 REQUIREMENTS archive exists. The v1.0 REQ list survives only in git (`ea22271:.planning/REQUIREMENTS.md`).
   - The v1.1 audit (dated 2026-09-11) covers phases 6/7/8 only. Phase 8.1 (2026-09-13) was never audited.
10. **Backlog ID collision.** "999.4" is the host-split Cursor status line on `main` (`main:.planning/ROADMAP.md:131`) and the ponytail skill-set on the v1.3 branch (`R/.planning/ROADMAP.md:332`).
    - The main todo `2026-10-12-promote-cursor-statusline-poc-into-999-4.md` targets the `main` meaning, so merging v1.3 will clobber one of them.

Soft deferrals, fine to let die: the PreToolUse real-time enforcement (`03-CONTEXT.md`), the local HTTP server (`05-CONTEXT.md`, explicitly non-committed), and the "raise a GSD upstream proposal" note for the shared core (`04-CONTEXT.md`).

## 3. PRD scope that was never planned or was silently dropped

- **Config-doctor PRD:** a skill wrapper plus a Checks Catalog doc, and the full apply set. Superseded or deferred as above.
- **Opencode-providers PRD:** a confirm-before-remove step.
- **Tool-substitution PRD, User Acceptance:** "the model demonstrably references the injected explanation". It was flagged as manual testing, and I found no evidence it ever happened. Unverified, low confidence.
- **Usage-metrics PRD:** the deferred axes (above).
- **Multi-CLI PRD:** the catalog-path wiring. Superseded by amendment, which leaves dead validator code.

## 4. Stale verifications and stale claims

- `06-VERIFICATION.md` cites `skills/ai-kit-agents-md-rules-checker/SKILL.md` and `tests/test_ai_kit_agents_md_rules_checker.py`, and neither exists any more.
- The v1.1 audit §3 cites `ai-kit-agents-md-rules-checker.py --help`, which is also gone.
- `08-` and `08.1-VERIFICATION.md` pass on symbols that are deleted on the branch (`TestRateBurnRatio`, `util_rate_burn_ratio`).
  - `R/.planning/PROJECT.md:155` ("burn-pace coloring — v1.1") and the Key Decision at `PROJECT.md:264` (marked "Good") are therefore stale on the branch.
- `03-VERIFICATION.md` has the placeholder timestamp `verified: 2026-09-09T00:00:00Z`.
  - REQ-tool-substitution-detection-composition still claims `registry.toml` `audience` is used.
- `PROJECT.md:204` says "No v1.2 phase has a Nyquist VALIDATION.md", but `15.1-VALIDATION.md` exists.
- **README:**
  - The Contents table (`R/README.md:26-46`) has no rows for `ai-kit-usage-metrics` or `ai-kit-spec-execute-superpowers`. The README contains 0 occurrences of "usage-metrics".
  - The Layout block (`README.md:501`) lists a `commands/` directory, which does not exist.
  - `README.md:517` says "`make test` runs the full suite on system python3", but test-integration and e2e-test use `uv run` (`Makefile:52,58`).
- **AGENTS.md:** line 124 links `.claude/cli-environment.md`, which is gitignored (`.gitignore:8`) and absent in any clone.
- **plugin.json:** the description still says "slash commands" and lists only the 2025-era skills.

## 5. Ponytail lens — delete candidates

- **curated-config v1 (11 subcommands).**
  - Against: never used by the user, judged "did little", and v2 replaces it.
  - Recommendation: delete when v2 lands. Do not maintain both.
- **`model_catalog.py` `native_runtime` validation** (`model_catalog.py:53,157-163`).
  - Against: by the project's own words, "forward-compatible only, no live producer" (`AGENTS.md:75-83`).
  - Recommendation: delete it, and keep the `config_io.py` copy.
- **The `"rate"` default ramp and `[ramp.rate]` compat parsing** (`status-line.py:172`, `statusline.toml.sample:149-152`). Both are unused since gap coloring.
- **The `classify` subcommand as a separate, never-run step.**
  - Option A: fold it into `run` as a one-line change. Classify is idempotent and resets first (`classify_loop.py:152-157`).
  - Option B: delete it.
  - Keeping it as an unrun step is the worst option.
- **The `000-ai-kit-overhaul-requirements.md` status table.** Archive it, or mark it historical.
- **The hand-copied `CURATED_SUBSTITUTIONS` in `family.py`.** Import it, or add a one-assert equality test.

## 6. Ranked summary

### Worth recovering (cheap, high value)

1. **Merge or cherry-pick the nested-runtime detection fix to `main`.** The live install misreports opencode and codex sessions started from Claude Code as `claude`.
2. **Run `classify` in `run`, or once by hand.** That reclassifies 210 real rows; today 0 rows have an inferred family.
3. **Wire Config Doctor apply for opencode `permission` and codex `sandbox_mode`.** These are the two security-relevant PRD rows. The engine already supports data-only row upgrades.
4. **Migrate or re-key the orphaned python stack cache.** The makefile checker returns `needs_research` for python today.

### To fix (correctness and doc debt)

1. **Pre-existing lint debt.** 12 ruff plus 6 pylint findings in the gate scope, re-deferred across 3 milestones. One quick task.
2. **ai-kit's own `claude_md_path`.** Change `./CLAUDE.md` (missing) to `./AGENTS.md`.
3. **The 999.4 ID collision** between `main` and the v1.3 branch. Renumber one before merging.
4. **README.** Add the missing usage-metrics and spec-execute-superpowers rows, drop `commands/`, and fix the `make test` wording. Fix or remove the broken `.claude/cli-environment.md` link in AGENTS.md.
5. **Record the gap-coloring change formally.** Add a REQ amendment and a PROJECT.md update, and close out the "draft" status on its spec.
6. **Config-doctor safety tests.** Make the 6 textual-dependent tests fail rather than skip under `make test-integration`, or assert that textual is importable there.

### To drop (no further investment)

- curated-config v1, once v2 ships.
- The dead `model_catalog` validator.
- The dead `rate` ramp.
- The PreToolUse and local-HTTP-server deferrals.
- Nyquist back-fill for archived v1.0/v1.1 phases. The tests are green, so back-filling validation docs for shipped phases is ceremony.

What I did not check: `make e2e-docker` and `make validate` were not run as whole targets; live cross-AI routes were not probed (the xai block is from memory); skill-judge scores were not re-run. Risk: the claims marked "inference" above rest on code reading only, without a live run.
