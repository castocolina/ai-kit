---
phase: "30"
slug: "phase-boundary-index-refresh-code-exploration-rules-and-lens"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-06"
---

# Phase 30 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| flow -> codegraph / graphify CLIs | index refresh at each boundary point and from the post-checkout runner | argv lists, checkout path |
| post-checkout hook -> detached runner | queue, job lock and log under the git common dir | checkout paths |
| setup -> global instruction files | rewrite of codegraph's sentence in four host files | file bytes, backups |
| boundary -> `.aikit/brief/SKILL.md` | brief read by researcher, planner, executor and implementers | file and symbol names, doc paths |
| setup-dev -> package managers | installs missing flow tools on the owner's machine | package names |
| GSD hooks -> ai-kit-fold.cjs | step and contribution dispatch from capability.json | verb, phase number |

---

## Threat Register

Built from the seven plans' `<threat_model>` blocks (40 rows: T-30-01..33 plus one T-30-SC per plan;
register authored at plan time). Evidence is at HEAD after the code-review fixes (0d7a35a); paths under
`skills/ai-kit-commit-fold/scripts/` unless noted. Audit: gsd-security-auditor (opus), ASVS L1.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-30-01 | Tampering | flow_index tool calls | high | mitigate | argv lists with `cwd=top` (`flow_index.py`); space and non-ASCII path test (`tests/test_flow_index.py`) | closed |
| T-30-02 | Denial of service | `index --detach` | high | mitigate | `start_new_session` Popen, `suppress` returning 0 (`flow_index.detach`); e2e checks git returns before any job ends (`tests/test_flow_index_e2e.py`) | closed |
| T-30-03 | Information disclosure | index outputs | medium | mitigate | `ensure_excluded` adds `.codegraph/`, `graphify-out/`, `.planning/graphs/` to `info/exclude`; porcelain-empty e2e | closed |
| T-30-04 | Tampering | foreign locks | medium | mitigate | GSD rebuild lock only read and waited on (`fold_adapters.index_lock_wait`); lock-unchanged tests | closed |
| T-30-05 | Tampering | real HOME | high | mitigate | writes only to the checkout and the common dir; scratch HOME fixtures; runner sets HOME and `AI_KIT_REFUSE_REAL_HOME` (`tools/run_unittest_parallel.py`) | closed |
| T-30-06 | Tampering | `.graphifyignore`, GSD config | medium | mitigate | append-only atomic write of one line (`fold_adapters.index_ensure_graphifyignore`); refresh leaves `.planning/config.json` byte-identical (`test_graphignore_holds_milestones_before_the_first_graphify_build`, added 0d7a35a) | closed |
| T-30-07 | Tampering | rule-text drift | medium | mitigate | AGENTS.md and R07/R08 drift checks (`tests/test_rules_docs.py`); advisor tokens appear in `RULE_CLAUSES[0]` (`test_advice_tokens_match_the_code_exploration_rule`, added 0d7a35a) | closed |
| T-30-08 | Repudiation | runbook overclaims | low | mitigate | `docs/run-book/graphify.md`, pinned in `tests/test_rules_docs.py` | closed |
| T-30-09 | Tampering | global_rules.apply | high | mitigate | bytes-only `replace_in_block` (`tools/marked_block.py`); CRLF, non-ASCII, no-final-newline, outside-block fixtures (`tests/test_global_rules.py`) | closed |
| T-30-10 | Tampering | lost update | medium | mitigate | re-read before replace (`tools/global_rules.py`); `before_replace` test | closed |
| T-30-11 | Tampering | symlink swap | medium | mitigate | realpath and isfile checks; `mkstemp` in the target dir with mode kept | closed |
| T-30-12 | Tampering | tests vs the real HOME | critical | mitigate | REFUSE guard in `tools/setup.py main()`; every `_ScratchHome` test asserts each `global_instruction_paths(env)` path lies under its scratch HOME (`tests/test_global_rules.py` setUp, added 0d7a35a; the wizard path calls the same resolver) | closed |
| T-30-13 | Repudiation | missing backup | high | mitigate | 0o600 backup claimed with `os.link`; failed backup skips the write; collision tests | closed |
| T-30-14 | Tampering | flow_brief.mentions | medium | mitigate | `re.escape` with word guards; atomic write; `a.b` test | closed |
| T-30-15 | Spoofing | stale brief | medium | mitigate | stamp lines and ignore-other-unit text (`flow_brief.py`); brief rewritten at every point | closed |
| T-30-16 | Repudiation | brief overclaims | low | mitigate | "mentions" wording only, pinned in `tests/test_flow_brief.py` | closed |
| T-30-17 | Information disclosure | `.aikit/` committed | low | mitigate | `ensure_excluded(.aikit)` before writes; `.gitignore` | closed |
| T-30-18 | Denial of service | lock waits | medium | mitigate | 600 s deadline, brief still written (`flow_boundary.py`) | closed |
| T-30-19 | Denial of service | advisor on Grep/Glob | medium | mitigate | no subprocess in `tools/hooks/advisor_core.py`; fail-open | closed |
| T-30-20 | Elevation of privilege | setup_dev installers | high | mitigate | fixed argv tuples, no shell (`tools/setup_dev.py`); unverified commands labeled; argv test | closed |
| T-30-21 | Elevation of privilege | sudo | high | mitigate | no `sudo` in any argv (test); permission failure reported with its manual command | closed |
| T-30-22 | Elevation of privilege | ai-kit-fold.cjs verbs | high | mitigate | VERBS table and PHASE regex; `spawnSync` argv; unknown-verb e2e | closed |
| T-30-23 | Tampering | config-set arrays | medium | mitigate | every `agent_skills` list keeps jev (live `.planning/config.json`); check in `tools/check_dogfood.py` | closed |
| T-30-24 | Information disclosure | absolute paths in config | low | mitigate | no home path in config (live); drift check and test | closed |
| T-30-25 | Elevation of privilege | trusted_global_roots | medium | mitigate | exactly `~/.agents/skills` (live); drift check and test | closed |
| T-30-26 | Tampering | brief text in implementer prompts | low | mitigate | brief holds names and paths only; unit-brief line pinned in `tests/test_ai_kit_spec_superpowers.py` | closed |
| T-30-27 | Denial of service | index queue | medium | mitigate | `launch_runner` on lock release; tests | closed |
| T-30-28 | Repudiation | stale graph reported fresh | medium | mitigate | `_graph_built_at_head` check; stale and `{}` tests | closed |
| T-30-29 | Tampering | wizard writes unreviewed files | high | mitigate | `reviewed=` passed from the wizard; skip logic; tests | closed |
| T-30-30 | Denial of service | unreadable file aborts doctor | medium | mitigate | `unreadable` status; `summary` never raises; test | closed |
| T-30-31 | Spoofing | wrong-unit stamp | medium | mitigate | `ref_mismatch` refusal before any write; tests | closed |
| T-30-32 | Denial of service | setup-dev offline | medium | mitigate | no Makefile prerequisite; `_step` and `main` always exit 0; tests | closed |
| T-30-33 | Repudiation | cross-AI skips boundary and brief | medium | mitigate | `Unit brief:` contribution in `capability.json`; pinned in `tests/test_flow_docs.py` and the e2e | closed |
| T-30-SC (01, 02, 03, 04, 06, 07) | Tampering | package installs | low | accept | no package added in these plans (uv.lock and pyproject untouched) | closed (accepted) |
| T-30-SC (05) | Tampering | setup-dev package installs | high | mitigate | each install target checked live, read-only, 2026-11-06 (`tmp/phase30-close/verify-installs.sh`): `uv tool list` shows `pre-commit` and `graphifyy`; `gh extension list` shows `github/gh-stack`; `brew info gh` is the formula `gh` (cli.github.com); `pnpm view @colbymchenry/codegraph` is github.com/colbymchenry/codegraph 1.6.2, the installed version. No executor ran an install (fakes only) | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-30-01 | T-30-SC (01, 02, 03, 04, 06, 07) | These plans add no package; nothing to verify beyond the unchanged lock file | plan-time disposition (accept) | 2026-11-05 |

Orchestrator-pending (not a threat): before a fresh-machine `make setup-dev`, the orchestrator
confirms the five install commands in `tools/setup_dev.py` `TOOLS`. On this machine all five tools
are present, so the target installs nothing.

---

## Security Audit 2026-11-06

| Metric | Count |
|--------|-------|
| Threats found | 40 |
| Closed | 40 |
| Open | 0 |

First pass (auditor, at 76fa531): 36 closed, 4 open (T-30-12 critical, T-30-SC (05) high, T-30-06 and
T-30-07 medium). Each gap was closed in this pass: three tests added in 0d7a35a, and the install
targets checked live.
