---
phase: "21"
slug: "cursor-live-validation"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
created: "2026-10-19"
---

# Phase 21 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| detection -> cursor CLI | PATH lookup with a realpath-basename guard for the bare `agent`; list argv, no shell; the user's `cursor-agent` shell function is never executed | model listing (medium) |
| cross-AI runner -> cursor-agent | headless dispatch under a scratch HOME outside the repo with the login symlinked (never read); process groups and environ-matched workers reaped | prompts, scratch files (high) |
| smoke harness -> real home | strict protected-set snapshot (hashes and labels, tree hashes for `~/.cursor/agents` and `skills`); `--host-rewrite` only in the user's interactive script | config hashes (high) |
| evidence -> repo | names-only env lists, placeholders, `secret-scan` and `$HOME` greps | tool output (medium) |

---

## Threat Register

Evidence from the gsd-security-auditor run (2026-10-19, after the code-review fixes).

| Threat | Cat | Sev | Disp | Evidence |
|---|---|---|---|---|
| T-21-01 | EoP | high | mitigate | `detection.py:168-189` resolves PATH only through `which_fn`. `detection.py:350` passes list argv to the injected `run_fn` with no shell. `tests/test_arch.py:367,538` forbids `shell=True` in the spec family. `tests/test_ai_kit_spec.py:2283` asserts the call has no shell. |
| T-21-07 | Tamper (cost) | medium | mitigate | `tests/fixtures/cursor_models.txt` is pinned at 265 ids and 79 `-fast` (`tests/test_ai_kit_spec.py:1546-1550`). `tests/test_cursor_agents.py:94-106` requires each pin to be in the fixture, not end in `-fast`, and have a `-fast` twin. |
| T-21-02 | Tamper | medium | mitigate | All listing tests use a fake `run_fn`. `snapshot --check` was recorded after each task (`21-01-SUMMARY.md:54`). No schema bump. |
| T-21-18 | Tamper (cost) | high | mitigate | `cursor-agents/grok-worker.md:4` is `grok-4.7-medium` and `composer-worker.md:4` is `composer-2.5`. Both are explicit, in the fixture (lines 13 and 30), and not `-fast`. The test above pins the set exactly. |
| T-21-08 | Spoofing | medium | mitigate | `tests/test_cursor_agents.py:87-92` requires name == stem and no `gsd-` prefix. `tests/test_curated_config_e2e.py:313-334` checks the live catalog, fails when the query fails and node is present, and checks the names are disjoint from the catalog. |
| T-21-17 | EoP | low | mitigate | `tests/test_cursor_agents.py:109-126` uses a list argv with `check=False`, a 30 s timeout, and a skip when node is absent. `gsd_catalog.py:128-146` uses list argv, `check=False`, a 10 s timeout, and returns None on failure. |
| T-21-06 | Tamper | high | mitigate | `gsd_curated_eval.py:4107-4152` builds the installer env from `INSTALL_ENV_KEEP` plus the throwaway HOME and XDG dirs, never from `os.environ`. `gsd_curated_eval.py:205` strictly lists `~/.gsd`, and `:196` strictly hashes `~/.gsd/defaults.json`. `snapshot ok` is recorded in `21-SMOKE-CURSOR.md`. |
| T-21-19 | Tamper | medium | mitigate | `gsd_curated_eval.py:206-211` strictly hashes `cli-config.json` and `hooks.json`. `:316-317` tree-hashes `~/.cursor/agents` and `skills`, following the WR-04 fix. `assert_no_probe` is called at `:2827`, `:3201` and `:4169`. The G6 test `test_cursor_agents_skills_hooks_are_protected` is in `tests/test_gsd_curated_eval.py`. |
| T-21-09 | Tamper (supply chain) | high | mitigate | `gsd_curated_eval.py:4071-4108` pins the cached installer to the gsd-core `VERSION`, aborts on a `package.json` version mismatch, and fails with "never npx in the smoke". |
| T-21-20 | Tamper (cost) | medium | mitigate | `roles.py:114,171,244` skips `fast_twin_of` candidates. `21-03-SUMMARY.md:95,151` records the artifact check: 35 resolved models, no `-fast`. See Notes: this is a one-off check, not a standing test. |
| T-21-03 | Info disclosure | medium | mitigate | My own run found `secret-scan` exit 0 over the phase directory. The `$HOME` grep also found nothing (the earlier `$HOME` literal search over `.planning/phases/21-cursor-live-validation` printed no lines). |
| T-21-04 | EoP | high | mitigate | `cursor-prompt.txt` names only `bash tmp/p21/headless/run-smoke.sh` and forbids reading credentials or editing tracked files. `gsd_curated_eval.py:667-675,688,4265,4585` runs `refuse_repo_apply` before every real apply. `21-SMOKE-CURSOR.md` shows `tree=clean`, and my `git status --porcelain` was clean. |
| T-21-22 | Info disclosure | high | mitigate | `teardown.txt` shows `login symlink intact: yes` and `scratch home removed: yes`. `21-SMOKE-CURSOR.md` lists env names only. My `secret-scan` was clean and a grep for `authInfo`/`@gmail` in committed evidence found no email or authInfo values (only plan/research prose). |
| T-21-21 | Tamper | high | mitigate | `run-smoke.sh` is recorded in `21-SMOKE-CURSOR.md`, and the evidence documents `CURSOR_CONFIG_DIR` and the XDG dirs under the scratch home. The evidence also states the isolation limit. `snapshot ok` is recorded for plan04, plan05 and plan06. |
| T-21-05 | DoS | medium | mitigate | `21-SMOKE-CURSOR.md` "Process proof": 12 spawn pgids empty, `escaped workers: none`, `ps-final` reconciled. `21-06-SUMMARY.md:213,255,383-391` repeats the leak check. |
| T-21-23 | Tamper | high | mitigate | Same throwaway HOME as T-21-06. `snapshot --check` against the plan04 baseline printed `snapshot ok` (`21-SMOKE-CURSOR.md` Phase gates). |
| T-21-10 | Info disclosure / tamper | medium | mitigate | `21-04-PLAN.md:26` and `21-04-SUMMARY.md` record the anchored `/tmp` path guard (directory, not a symlink, owned by the user). `teardown.txt` and `ls /tmp/p21-cursor-home.*` (no match) confirm the removal. The `test -L` symlink check passed. |
| T-21-13 | EoP | high | mitigate | `21-SMOKE-CURSOR.md` Session section has the line `cursor-agent invoked only by the runner`. `21-04-SUMMARY.md:116` confirms the gate passed. |
| T-21-24 | Tamper (supply chain) | high | mitigate | Same mechanism as T-21-09: `gsd_curated_eval.py:4071-4108`. |
| T-21-12 | Repudiation | medium | mitigate | `SKILL.md:254` says "validated headless ... interactive confirmation ... **pending**". The matrix evidence is `matrix ran: 420 checks`. `21-SMOKE-CURSOR.md` quotes the single `headless verdict: green (attempt 1 ...)` line and the amended SPEC R3 rule. A test pins the label (`test_cursor_label_lifted_with_evidence_pointer`). |
| T-21-15 | Repudiation | medium | mitigate | `21-SKILL-JUDGE.md:77` reads `Verdict: UNRESOLVED (owner review ...)`. It never claims PASS: pi scored 114/120, below its 116 floor. The recorded digest `85da5a6682d937c5` now differs from the tree's `f0c43a5da52a587d`, which is correctly treated as stale (see Unregistered flags). |
| T-21-26 | Info disclosure | medium | mitigate | `21-05-SUMMARY.md:77,139` records `.err` files redacted to `<home>` before the batch move. My `secret-scan` and `$HOME` grep are clean over `skill-judge/` and the evidence. |
| T-21-27 | EoP | low | mitigate | `21-SKILL-JUDGE.md` Rounds: `--mode review`, `--prefer pi` only, 600/630 s bounds. The runner withheld a report on a dirty tree (`contract_violation`), which shows the tree-clean requirement is enforced. |
| T-21-25 | Tamper | medium | mitigate | `21-05-SUMMARY.md:61` records `snapshot --check plan05.before.json` giving `snapshot ok`. |
| T-21-28 | Tamper | high | mitigate | Design present in `21-INTERACTIVE-CURSOR.md`: the `CURSOR_CONFIG_DIR` default-dir guard (line 55), digest of the three user-owned keys before and after, the limit stated honestly, and `--host-rewrite` restricted via `choices=(CURSOR_CLI_CONFIG_LABEL,)` (`gsd_curated_eval.py:5003-5010`). The strict entry stays strict without the flag (`:209-211`), and `hooks.json` plus the `agents`/`skills` hashes stay strict. Six tests are recorded in `21-06-SUMMARY.md:91`. The runtime result of the user's run is pending (see Human verification). |
| T-21-29 | Info disclosure | high | mitigate | The digest one-liner (`21-INTERACTIVE-CURSOR.md:55`) hashes only `modelParameters`, `subagentModels` and `exploreSubagentModel`, and prints only sha256. The env dump keeps names only (`cut -d= -f1`). `authInfo` is never touched. The phase directory passes `secret-scan`. |
| T-21-30 | EoP | low | **accept** | See Accepted risks. |
| T-21-16 | DoS | medium | mitigate | `21-INTERACTIVE-CURSOR.md:120-124`: the probe only lists workers. It uses the `AIKIT_P21_PROBE=1` marker and a read-only `/proc/<pid>/environ` match for `probe-owned`, and labels everything else `unidentified`. There is no automatic kill and no age rule. |
| T-21-31 | DoS | low | mitigate | `21-06-SUMMARY.md:213,255,394` and `21-SMOKE-CURSOR.md` Phase gates: all 12 spawn pgids empty, the leak check matches 21-04's baseline, scratch home gone. |
| T-21-14 | Spoofing | high | mitigate | `cross-ai.mjs:420-433` realpath-basename-checks every scanned `agent` hit, and `bins` puts `cursor-agent` first (`:258`). Self-test cases cover the grok-first, cwd and spawn paths (`:2561-2660`). The tracked `.planning/scripts/cross-ai.mjs` is template 6 and `script_state` returns `pristine` (my check). `TEMPLATE_VERSION = 6` at `cross_ai.py:46`. `detection.py:177-197` has the same guard in Python, and `routing.py:281` calls `cached_binary_usable` (the WR-02 fix). |
| T-21-32 | EoP | low | mitigate | Self-test fakes live under the self-test tmp dir. The e2e `--self-test` passed in my run. |
| T-21-33 | Tamper | low | mitigate | `21-07-SUMMARY.md:54` records the protected-snapshot delta. Only the one authorized `.planning/scripts/cross-ai.mjs` change is expected. |
| T-21-SC | Tamper | high | mitigate | No `pyproject.toml`, `uv.lock` or `package.json` commits since 2026-10-17. The smoke uses the cached gsd-core copy with no registry fetch (`gsd_curated_eval.py:4108`). |
| T-21-11 | Info disclosure | low | mitigate | The literal scratch-home path in four evidence lines was redacted to `<scratch-home>` by the orchestrator after the audit; the `p21-cursor-home` grep over the phase dir is clean |

All 34 threats (T-21-01..T-21-33 plus T-21-SC) are closed or accepted.

---

## Accepted Risks Log

- **T-21-30** (EoP, low): the optional ROADMAP SC5 probe, `command cursor-agent -p --trust`, runs in the user's own shell and account. It uses the PATH binary and never the shell function. It runs in a scratch `mktemp -d` workspace with a fixed prompt, after step 4, and the directory is removed with `rm -rf "$W"` (`21-INTERACTIVE-CURSOR.md:117-123`). The risk is accepted because the probe is optional and bounded.
- **IN-05** (informational): an empty PATH entry resolves to the cwd, so an untrusted checkout could supply its own `agent` or `cursor-agent`. This is documented in `runner.md` and mirrored in both resolvers. For guarded `agent` the realpath guard still applies, but an unguarded `cursor-agent` placed in the cwd would be accepted. It is an accepted, documented limit.

---

### Unregistered flags

None of the SUMMARYs has a `## Threat Flags` section. The items below are from the SUMMARYs, reviews and code.

1. The skill-judge gate is not passed, and `SKILL.md` and `references/` changed again after the judged digest. The current tree digest is `f0c43a5da52a587d`; the verdict records `85da5a6682d937c5`. `21-REVIEW-FIX.md` states the judges must re-run. This is a process and repudiation concern, not a mitigation gap, because no over-claim is made.
2. The interactive Cursor TUI run (`21-INTERACTIVE-CURSOR.md`) has not happened. The T-21-28/29/16 mitigations exist as script design and harness code, but their runtime outcome is unverified, and the phase stays `human_needed`.
3. `21-REVIEW-FIX.md` marks CR-01, WR-01, WR-02 and WR-06 as "requires human verification". These are resolver and parser logic changes. They are not tracked in the register, but the code and tests I checked are consistent with the stated intent.
4. `21-SMOKE-CURSOR.md` still quotes `template=5` in its Session and Runner note. It now describes a superseded runner (template 6), so the historical evidence is not re-rendered.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-19 | 34 | 33 | 1 (T-21-11, low, below threshold) | gsd-security-auditor (ASVS 1, block_on high) |
| 2026-10-19 | 34 | 34 | 0 | orchestrator: T-21-11 redaction |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-19
