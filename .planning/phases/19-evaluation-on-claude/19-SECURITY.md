---
phase: "19"
slug: "evaluation-on-claude"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-17"
---

# Phase 19 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| eval harness -> headless `claude -p` agent | An unattended agent with Bash runs in a scratch project on the real login; it gets an allowlisted env (`CELL_ENV_KEEP` plus the fixture env and HOME), `--setting-sources project`, and its process group is killed on any unwind | prompts, scratch files (high) |
| agent transcript -> committed evidence | Grade records keep product reports only; transcripts are trimmed with placeholders applied before the cut; `secret-scan` (one canary per shape) gates every evidence commit | tool output (medium) |
| harness -> real home | Read-only: a protected-set snapshot (hashes and labels, never contents; the credentials file excluded) is diffed around every batch and optionally per cell (`run --snapshot`) | config hashes (high) |
| smoke / matrix -> project config | Real applies only on `mkdtemp` scratch projects behind `refuse_repo_apply`; inventories on a seeded scratch cache with `assert_no_probe` | config (high) |
| skill judges -> repo | Review-mode runner on a clean tree; output only under scratch, moved after the last judge exits | judge reports (medium) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-19-01 | Repudiation | matrix oracle | high | mitigate | oracle from plan entries plus live tables, never the applied config; Control 1 must fail every unoverridden agent or the run exits `control 1 vacuous`; Control 2 must pass | closed |
| T-19-02 | Tampering | scratch bundles and real HOME | high | mitigate | every bundle under `tempfile.mkdtemp()`; `GSD_HOME` scratch; `test_repo_config_untouched` hashes the repo config and runner before and after; nothing under the home directory is written; `<home>/.cursor/cli-config.json` is a strict snapshot entry so a ... | closed |
| T-19-03 | Information disclosure | snapshot output | medium | mitigate | labels only (`<home>`, `<worktree>`), hashes never contents; `test_no_absolute_paths_or_values_in_output`; the credentials file is excluded from every set and never read | closed |
| T-19-04 | Denial of service | stderr warnings or a hung node child | low | accept | stdout JSON only (Pitfall 8); apply and resolve calls carry the e2e tier's timeouts; pid leak check | closed |
| T-19-SC | Tampering | npm/pip/cargo installs | high | mitigate | this plan installs nothing | closed |
| T-19-05 | Tampering | fixture builder | high | mitigate | every write under the run dir; `GSD_HOME`, `XDG_CACHE_HOME`, `TMPDIR` scratch; the home directory is never written; unit tests use a scratch home; `assert_no_probe` proves the seeded cache is fresh (runtimes, sidecar, schema) before any product ... | closed |
| T-19-06 | Information disclosure | `run.json` | medium | mitigate | only the named init fields, cost, return codes, reaped pids and the sanitized dir name are recorded; the child env is never written to disk | closed |
| T-19-07 | Tampering | `~/.claude` host state by the headless child | high | mitigate | `--setting-sources project`, scratch cwd outside the repo and outside `~/.claude`, `projects`-key assertion, transcript-dir deletion; before/after `snapshot --check` in the orchestrator plans | closed |
| T-19-42 | Repudiation | RED-b evaluating an installed copy of the skill instead of the worktree's v1 script | high | mitigate | the materialized v1 SKILL.md has its resolver block pinned to the run-dir entrypoint (every other byte the `7009d22^` text, by test), `CLAUDE_PLUGIN_ROOT` dropped from the cell env, and `entrypoint_shadowed` recorded as a harness failure on any ... | closed |
| T-19-43 | Repudiation | an infrastructure failure graded as a skill verdict | medium | mitigate | a non-zero turn exit, a missing `result` event or `is_error: true` stops the continuation and exits 1 as a harness failure; the re-run rule of 19-06 applies, never a RED/GREEN cell (review cycle 2) | closed |
| T-19-48 | Tampering | RED-b's v1 detect steps running a bare `detect-runtimes` that lists real non-Claude CLIs (`cursor-agent models` rewrites `~/.cursor/cli-config.json`) | high | mitigate | the v1 entrypoint is a launcher that puts `DIR/fakebin` first on `PATH` inside its own process; every non-claude `RUNTIMES` binary name is a logging wrapper serving only the seeded opencode/cursor listings; `_self_check_v1_detect` proves the outputs equal ... | closed |
| T-19-49 | Tampering | ambient `review-spec.toml` changing or aborting fixture construction | medium | mitigate | `_drop_model_less_rows` removes the only trigger of `cfg_resolve` on the fetch path; `test_ambient_review_config_cannot_affect_fetch` both halves (review cycle 3) | closed |
| T-19-50 | Denial of service | the stray reaper signalling the harness's own ancestor or its group | medium | mitigate | `ps_fn` carries the ppid column; the whole ancestor chain and every group on it are spared; `test_reaper_spares_higher_ancestor_in_other_group` with its non-vacuity half (review cycle 3) | closed |
| T-19-08 | Elevation | `inventory` executing a scratch project's gsd-core | low | accept | the symlink points at the worktree's own gsd-core (trusted) | closed |
| T-19-09 | Repudiation | grader | high | mitigate | one wrong-input test per check, including the vacuous cases (zero approvals, post-write disclosure, refused preview, a no-op `ensure-project` counted as the first write, an Anthropic lane behind a Cursor id, a router only in `.new`, a v1 hook whose ... | closed |
| T-19-10 | Information disclosure | trimmed transcripts and graded evidence | medium | mitigate | placeholders for run dir, home and worktree; `secret-scan` with a canary self-check runs before every evidence commit | closed |
| T-19-11 | Tampering | transcript content driving file reads | low | mitigate | the grader reads only files under the run dir it is given; commands are matched as strings, never executed | closed |
| T-19-12 | Tampering | real apply on the repo root | high | mitigate | `refuse_repo_apply` on every real-apply path (realpath compare), unit-tested both ways; tree hash around the dry run; protected-set snapshot before and after the whole smoke | closed |
| T-19-13 | Tampering | fault injector | medium | mitigate | edits a copy under the scratch work dir only; JSON load and dump, never string splicing; the original plan file is not touched; the perturbed key is written only to scratch project (a) through the guarded `config_set` path | closed |
| T-19-44 | Tampering | live `inventory` enumerating non-Claude CLIs against the real home (the cursor listing rewrites `~/.cursor/cli-config.json`) | high | mitigate | seeded scratch `XDG_CACHE_HOME` from `_seed_caches`; `assert_no_probe` before step 1; cache byte identity after every inventory; 19-01's strict `<home>/.cursor/cli-config.json` entry as the detective backstop (review cycle 2) | closed |
| T-19-45 | Repudiation | a rollback experiment that never exercised restoration | medium | mitigate | `perturb_before_fault` queues one real write ahead of the rejected key; the recorder proves it was written and the byte check proves it was undone; `test_fault_step_requires_undone_write` (review cycle 2) | closed |
| T-19-14 | Information disclosure | project (b) evidence | medium | mitigate | key paths only; `test_project_b_records_key_paths_not_values`; placeholder rendering tested | closed |
| T-19-15 | Denial of service | a failing step aborting before the snapshot comparison | low | mitigate | every step records and continues; step 7 always runs; scratch dirs removed in `finally` | closed |
| T-19-16 | Tampering | real apply on ai-kit (the one-way door, D-03) | high | mitigate | `refuse_repo_apply` guard; `snapshot --check` before and after the smoke and the plan; `git status --porcelain` empty; the evidence's `## Protected set: unchanged` line | closed |
| T-19-46 | Tampering | `inventory` enumerating non-Claude CLIs against the real home (`cursor-agent models` rewrites `~/.cursor/cli-config.json`) | high | mitigate | seeded scratch cache, `assert_no_probe` before step 1, byte identity after every inventory (19-04); `<home>/.cursor/cli-config.json` in the strict snapshot (19-01), so a write stops the plan (review cycle 2) | closed |
| T-19-17 | Information disclosure | values from the real global defaults or home paths in committed evidence | medium | mitigate | key paths only; placeholder rendering; `grep -F -- "$HOME"` prints nothing; `secret-scan` with canary before the commit | closed |
| T-19-18 | Tampering | a defect fix that changes product behavior without a test, or a helper misread routed as a product fix | medium | mitigate | the triage table separates harness failure, environment and product defect; Run rule 6 requires the failing regression test first, one cited `fix(19-05)` commit, the unit group green, the smoke repeated from step 1 and `product_commit` refreshed | closed |
| T-19-19 | Denial of service | orphaned node or helper processes | low | mitigate | pid-snapshot leak check; scratch dirs removed in `finally` | closed |
| T-19-20 | Tampering | headless agent escaping the scratch project (Pitfall 6, residual risk U-1) | high | mitigate | scratch cwd outside the repo, target path in the prompt, `--setting-sources project`, per-batch `snapshot --check` and `git status --porcelain` (detective); any strict drift stops the batch and is recorded | closed |
| T-19-21 | Tampering | `~/.claude` host state (settings, listings, `~/.claude.json`) | high | mitigate | strict set hashed before and after each batch; `projects`-key assertion and transcript-dir deletion inside `run`; the exact dir re-checked from `run.json`; flags per the spike | closed |
| T-19-22 | Information disclosure | committed transcripts | medium | mitigate | trimmed transcripts only (assistant text, commands, result heads) with placeholders; `secret-scan` with canary before `git add`; raw jsonl stays under gitignored `tmp/` | closed |
| T-19-23 | Denial of service | OAuth quota and cost | medium | mitigate | six runs at sonnet/medium, one sample per cell, re-run only on harness failure or after a defect fix; `total_cost_usd` recorded per run | closed |
| T-19-24 | Repudiation | skill edits without evidence (pre-writing) | medium | mitigate | the evidence table gates every hunk; each pin comment names its RED or GREEN cell; a diff hunk without a row is a plan failure | closed |
| T-19-25 | Tampering | a new bash example with `--force`, a wrong flag, machine-specific wording, or a reordered step | medium | mitigate | `TestSkillDocCommands` (entrypoint, parser, no `--force`, no machine phrases, required phrases, `test_v2_steps_in_order`) runs before every commit | closed |
| T-19-26 | Repudiation | stale GREEN rows after a REFACTOR edit, or rows naming uncommitted bytes | high | mitigate | every row carries its digest; every edit is committed before its re-run; any edit supersedes all GREEN rows and re-runs B-E; `digest --check` gates Tasks 2 and 3 | closed |
| T-19-27 | Repudiation | a jev answer presented as consent or as a pass | medium | mitigate | the row stays `fail`; the verdict text is `UNRESOLVED (user decision required; jev advises <choice>)`; listed under `## Human needed` | closed |
| T-19-28 | Tampering | host state and scratch escape (as T-19-20/T-19-21) | high | mitigate | same controls: per-batch `snapshot --check`, `git status` scoped, `run.json` harness checks, exact transcript-dir deletion | closed |
| T-19-29 | Repudiation | judge evidence describing other bytes than the committed skill | high | mitigate | per-row digest; `D_before == D_after`; `digest --check` over both evidence files gates the commit; 19-10's committed-digest check | closed |
| T-19-30 | Repudiation | a review-mode judge voided by a concurrent repo write (`contract_violation`) | high | mitigate | all output under `tmp/judge/`; no write outside `tmp/` while a judge is alive; batch move after the last exit; timeline in the SUMMARY | closed |
| T-19-31 | Repudiation | PASS without an independent judge, or a PASS that discards an available judge's Critical/Important finding, or a voided attempt waived as unavailability | high | mitigate | the phase rule needs one pi pass plus the in-session pass on the same digest and no failing non-superseded row (18.1-22 form); a failing available judge -> PENDING; both pi unavailable -> BLOCKED recorded, never PASS; ... | closed |
| T-19-32 | Information disclosure | judge prompts, credentials, and judge output quoting a real path or value | medium | mitigate | only public skill text and the rubric copy are sent; credentials stay inside the pi CLI; no key is read or printed; every report passes `secret-scan` and the `$HOME` placeholder check in `tmp/judge/out` before the batch move | closed |
| T-19-33 | Repudiation | judge or GREEN evidence describing other bytes than the committed skill | high | mitigate | every fix committed before its re-runs; per-row digest; `D_before`/`D_after` per round; any fix supersedes every row of both files; `digest --check` gates every task | closed |
| T-19-34 | Repudiation | a jev answer read as the user's D-07 decision, an owner decision taken on an incomplete packet, or a ladder call that silently yields no answer | medium | mitigate | verdict text is `UNRESOLVED (user decision required; jev advises ...)` or `... jev unavailable)`; item, answer and verification recorded; the ladder gets a fence-free summary under `decide.py`'s 1500-character cap while the complete ... | closed |
| T-19-47 | Repudiation | a `harness-failed` GREEN cell carried as passing behavior | medium | mitigate | one fresh re-run per round; a persistent `harness-failed` cell keeps the stop rule unmet and the verdict `UNRESOLVED`; Task 2's verify rejects `PASS` beside a `harness-failed` `GREEN (sonnet)` cell (review cycle 2) | closed |
| T-19-35 | Repudiation | a review-mode judge voided by a concurrent repo write | high | mitigate | Run rule 9: `tmp/judge/` only while alive, batch move after the last exit, timeline per round | closed |
| T-19-36 | Tampering | a fix that reorders steps, drops a required phrase, or regresses a GREEN behavior to please a judge | high | mitigate | `TestSkillDocCommands` (with `test_v2_steps_in_order`) before every round commit; step order and `## Limits` heading kept (R-2); v1 promise (Run rule 8); the stop rule needs no GREEN regression on the final digest and `cells --column 'GREEN (sonnet)'` ... | closed |
| T-19-37 | Denial of service | hung judge or headless child; quota | medium | mitigate | runner deadline (`--timeout 1800`, outer 1830); at most two judges at a time; `run` turn timeout 900 s; cap 3 rounds; pid-snapshot leak check; `total_cost_usd` recorded | closed |
| T-19-38 | Repudiation | gate claims without output, or a gate dropped when its tool is absent | medium | mitigate | gate output pasted in the SUMMARY; `make e2e-docker` stays in the automated check; absence recorded verbatim as a failure routed for owner review | closed |
| T-19-39 | Repudiation | `JUDGED_COMMIT` naming other bytes than the live rows, or smoke and pressure evidence describing a previous product revision after a late `fix(19-10)` | high | mitigate | clean status over the judged paths before reading the sha; `digest --check` per evidence file and per GREEN column plus `cells --strict` in the same check; `product_commit:` of 19-SMOKE.md and 19-PRESSURE-TESTS.md must equal the last product commit, and a ... | closed |
| T-19-40 | Repudiation | a decision the run made on the owner's behalf left unlisted, or a withdrawn finding written into evidence as a defect | medium | mitigate | one consolidated `human_needed` index built from every evidence file and SUMMARY; `none` is written explicitly; the withdrawn v1 isolation finding is not copied anywhere (review cycle 2) | closed |
| T-19-41 | Denial of service | orphaned gate, container or child processes, or debris left in the tree | medium | mitigate | pid-snapshot leak check over node, helper, claude, pi, runner and container patterns; per-file stray comparison against the start-of-plan baseline (`git status --porcelain` plus `git ls-files -o -i`), so a new file inside `.claude/` is reported while ... | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

The register is the union of the ten PLANs' `<threat_model>` blocks (61 rows; T-19-SC repeats in every plan and T-19-48 in two, merged). Mitigations quote the plan; where the code review replaced a mechanism (19-REVIEW-FIX.md: CR-02, CR-03, WR-04, WR-05, IN-09, IN-10), the audit judged the current one. T-19-45 was open below the threshold at audit time: the plan's regression test `test_fault_step_requires_undone_write` had never been written. It was added after the audit (`tests/test_gsd_curated_eval.py`, TestReviewFixes) and covers the missing write, the restored bytes and the unrestored bytes.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-19-01 | T-19-04 | Only stdout JSON is parsed; apply and resolve calls carry the e2e tier's timeouts; a pid leak check runs | 19-01 plan (plan review) | 2026-10-17 |
| AR-19-02 | T-19-08 | `inventory` runs the scratch project's gsd-core through a symlink to the worktree's own trusted install | 19-02 plan (plan review) | 2026-10-17 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-17 | 51 | 50 | 1 (T-19-45, medium, below threshold) | gsd-security-auditor (ASVS 1, block_on high) |
| 2026-10-17 | 51 | 51 | 0 | orchestrator: T-19-45 test added |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-17
