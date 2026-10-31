---
phase: 27
slug: one-shot-goal-and-loop-prompt-skill
status: SECURED
threats_total: 44
threats_secured: 41
threats_accepted: 3
threats_open: 0
threats_open_nonblocking: 0
asvs_level: 1
block_on: high
audited: 2026-10-31
audited_head: d6f7cc5
---

# Phase 27 Security Audit

The register comes from the `<threat_model>` blocks of 27-01 to 27-14: 36 numbered threats
(`T-27-01` to `T-27-36`) plus the shared `T-27-SC` row (37 registered, all `mitigate`). The audit
(`gsd-security-auditor`, read-only, HEAD `19bb817`) also hunted for unregistered paths and found seven
(U1 to U7). Each registered mitigation was checked in the shipped code and tied to a passing test.

Verdict: SECURED. 37/37 registered rows closed, no high-severity gap. Of the seven unregistered
findings, four are fixed in this phase (`fix(27-secure)`, failing test first) and three are accepted
residual risks stated below. U8 is a process note, not a code threat.

## Verification runs (this audit)

- All 13 `tests.test_ai_kit_spec_goal_prompt_*` modules pass in a scratch HOME with
  `AI_KIT_REFUSE_REAL_HOME=1`; `git status` is clean afterwards.
- Adversarial probes against the CLI ran in a scratch repo under `tmp/` only: hostile plan titles and
  objectives (newline, `--from 9`, headings), an evil `cross_ai_command`, a symlinked `--out-dir`, a
  symlinked plan and a 3 MB Makefile and plan.
- Install surface: `uv.lock` and package files are unchanged; `pyproject.toml` gained two pyright
  `extraPaths` lines; the scripts import only the standard library and sibling modules.
- CR-01 (arbitrary `cross_ai_command` execution, fixed in `2b7d55e`) is confirmed: a foreign leading
  token, extra flags or a non-`cross-ai.mjs` script are never run (`TestReadiness`). No `shell=True`,
  `os.system`, `eval` or `exec` exists in `scripts/`; the two `subprocess.run` sites (`gp_host._run`,
  `gp_render._ignored`) take a list argv with a timeout and closed stdin.

## Threat register

| ID | Sev | Mitigation | Evidence | Status |
|----|-----|------------|----------|--------|
| T-27-01 | medium | Guard messages name the kind of finding, never the matched text | `gp_common.py:92-103`; `test_ai_kit_spec_goal_prompt_common` | CLOSED |
| T-27-02 | low | Fixtures live in temp dirs; `FAKE_HOME` is a literal never created | `tests/goal_prompt_fixtures.py:17` | CLOSED |
| T-27-03 | medium | Exact `packageName` equality, else `unverified` | `gp_scope.py:135`; `TestIdentity` | CLOSED |
| T-27-04 | medium | `phase_dir`/`state_path` never read; paths made relative | `gp_scope.py:8,95`; `TestPhases`, CLI test | CLOSED |
| T-27-05 | low | Only a backticked filename of a loaded plan becomes an edge | `gp_scope.py:156-170`; `TestPlans` | CLOSED |
| T-27-06 | medium | Only exit code, CLI names and booleans kept from probes | `gp_host.py:355-364`; `TestReadiness` | CLOSED |
| T-27-07 | high | List argv, no shell, timeouts, no model call | `gp_host.py _run`; `goal_prompt.py _gsd_json`; `TestReadiness`, CLI tests | CLOSED (U1 residual) |
| T-27-08 | medium | `absent` only from a positive help probe | `gp_host.py`; `TestPrimitives` | CLOSED |
| T-27-09 | medium | Commands built from fixed templates plus a script NAME | `gp_e2e.py:112-114`; `TestSignals` | CLOSED |
| T-27-10 | low | Skip `node_modules`/`.git`, files over 200 KB, 80 lines; links skipped; reads capped at 1 MiB | `gp_e2e.py`; `TestPtyAndMarkers` | CLOSED |
| T-27-11 | medium | Every marker row carries `verified` | `gp_e2e.py:53-64`; `TestBlocks` | CLOSED |
| T-27-12 | medium | Each strategy states its reason and an `unverified` label | `gp_matrix.py`; `TestRows` | CLOSED |
| T-27-13 | medium | `needs` predicate plus a property test over four host tables | `gp_matrix.py`; `TestProperties` | CLOSED |
| T-27-14 | high | Free text on one line; flag scan after line 1 | `gp_sections.py _one_line`; `gp_render.py FLAG_RE`; `TestGuards` | CLOSED |
| T-27-15 | high | `check_text` runs `scan_text` and the path check before any write | `gp_render.py check_text`; `TestGuards` | CLOSED (U6 residual) |
| T-27-16 | medium | `choose_path` never returns an existing path; exclusive create; output dir must resolve inside the repo | `gp_render.py choose_path, write_atomic`; `TestPlacement` | CLOSED (fixed in this audit, U2/U7) |
| T-27-17 | high | Plan titles single-line, quoted; same guard plus `--no-verify` check | `gp_render.py`; `TestSuperpowers` | CLOSED |
| T-27-18 | medium | Heading suffix `[unverified: <primitive>]` pinned | `gp_render.py:332-340`; `TestBlocks` | CLOSED |
| T-27-19 | high | jev is one advisory line in REPORT only | `TestDoneVariants` | CLOSED |
| T-27-20 | medium | Readiness warnings only on stdout, asserted absent from the file | `gp_render.py _readiness_warnings`; `TestCrossAiVariants` | CLOSED |
| T-27-21 | high | `shlex.split`, list argv, three read-only `query` subcommands | `goal_prompt.py:236-255`; CLI tests assert the argv | CLOSED |
| T-27-22 | medium | No temp root or fake home in any output | CLI and golden sweeps | CLOSED |
| T-27-23 | high | Temp HOME, `AI_KIT_REFUSE_REAL_HOME=1`, fake `node`, clean `git status` | `test_ai_kit_spec_goal_prompt_e2e` | CLOSED |
| T-27-24 | high | `## Unverified` section; per-marker lines pinned | `SKILL.md`; `test_ai_kit_spec_goal_prompt_skilltext` | CLOSED |
| T-27-25 | high | NEVER item; hand-off ends with "stop"; nothing executes the file | `SKILL.md` | CLOSED |
| T-27-26 | low | Drift test greps docs for machine paths | `skilltext`, `evals` | CLOSED |
| T-27-27 | high | Scratch HOME install smoke; guard on | `27-11-SUMMARY.md` (process evidence) | CLOSED |
| T-27-28 | low | No `wizard_app.py` left after the PTY run | `27-11-SUMMARY.md` | CLOSED |
| T-27-29 | high | Clean tree after every judge lane | `27-12-SUMMARY.md`; tree clean now | CLOSED |
| T-27-30 | high | `check_verdicts.py --gate`; acceptance only by an `Owner-decision:` line | fails closed today (see U8) | CLOSED |
| T-27-31 | medium | Read-only copy of nine skill-judge files | `27-12-SUMMARY.md` | CLOSED |
| T-27-32 | high | Live checks write ignored scratch only | `27-13-SUMMARY.md` | CLOSED |
| T-27-33 | medium | Unverified behavior is an owner capture; amendments dated | `27-OWNER-CAPTURES.md` | CLOSED |
| T-27-34 | medium | Regex and `scan_text` over every shipped text file | `evals` `test_no_machine_paths_or_secrets` | CLOSED |
| T-27-35 | high | Fake HOME and XDG, staged copies, tree unchanged after the error case | `test_ai_kit_spec_goal_prompt_evals` | CLOSED |
| T-27-36 | medium | Fixtures proven through the real CLI | `test_ai_kit_spec_goal_prompt_evals` | CLOSED |
| T-27-SC | high | No package installed | `uv.lock`, package files unchanged | CLOSED |

## Unregistered findings

| ID | Sev | Finding | Disposition | Commit / reason |
|----|-----|---------|-------------|-----------------|
| U1 | medium | `detect` runs the repo's own `node <path>/cross-ai.mjs --print-argv`, wherever it resolved, with the caller's full environment | Fixed in part: the script must resolve inside the repo (links and absolute paths out are refused) and credential-named variables are dropped from every probe child. **Accepted residual:** the repo's own runner script still runs, as it would under the repo's own tests; the name filter is not an allowlist | fix(27-secure): probe only a runner script inside the repo, without credential variables |
| U2 | medium | A symlinked `--out-dir` or goals directory wrote outside the repo | Fixed | fix(27-secure): keep the goal file inside the repo and create it exclusively |
| U3 | low | Symlinked plan files and `config.json` were read from anywhere | Fixed | fix(27-secure): skip symlinked plans and config, cap project file reads at 1 MiB |
| U4 | low | Unbounded reads of plans, Makefile and config | Fixed (1 MiB cap; `package.json` reads stay in the shared `gp_common` copy, which is held equal to its original) | same commit |
| U5 | low | Config strings (`runner.command`, reviewer names) echo into `detect` stdout unscrubbed | **Accepted:** the output goes to the local agent only; render refuses a key-shaped token before any write | none |
| U6 | low | `scan_text` covers `sk-` and `ghp_` shapes only | **Accepted:** the helper is a parity copy of three originals (27-01); widening it belongs to a change of all four | none |
| U7 | low | Check-then-replace race on overwrite | Fixed (exclusive hard link) | with U2 |
| U8 | info | `check_verdicts.py` reports a stale verdict: the package changed after round 3 | **Process:** no re-judge was run here; the phase is not skill-judge accepted at HEAD until a new round or an `Owner-decision:` line (see `27-OWNER-CAPTURES.md` item 7) | none |

## Not checked

The live OpenGSD and `/gsd-autonomous` paths and the cross-AI runner were not run for real, and the
27-11 to 27-13 procedures are process evidence only.
