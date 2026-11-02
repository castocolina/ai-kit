---
phase: "25"
slug: "quota-aware-cross-ai-subprocess-supervision"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-25"
---

# Phase 25 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| runner -> child CLI | each CLI runs with full permissions in the project tree |
| owner config -> runner | `--prefer`/`CONFIG.prefer` name the CLI; the runner must not widen that choice |
| child output -> classifier | stderr and stdout are untrusted text the model or provider controls |
| classifier -> status line / logs | composed lines reach GSD's error log and the Python relay |
| owner capture file -> `--classify-only` | a pasted capture is untrusted text |
| command line -> route flag | the flag decides retry behavior on quota |
| child output -> watcher | the watcher reacts to untrusted lines while the child holds full permissions |
| runner -> new session | a fresh full-permission agent starts over a tree another session changed |
| prompt -> dirty rule | the `<files>` list in the prompt widens what a new session may continue |
| runner -> router lane | repeated full-permission attempts against a quota-limited lane |
| runner logs -> GSD error log, Python relay | composed lines leave the process |
| orchestrator -> live supervisor | the file the delegated plans run through is replaced |
| catalog cache -> runner argv | a user-editable cache file decides a runner flag |
| skill text -> orchestrating agent | an agent follows these instructions with tool access |
| docs -> readers and agents | docs set what an agent believes the runner did |
| owner capture -> repo | a live capture can carry provider bodies with masked keys |
| orchestrator -> judge CLI | a real model call through the runner, review mode |
| orchestrator -> planning docs | amendments steer every later agent |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-25-01 | Elevation of privilege | `main` candidate loop | high | mitigate | only the first candidate spawns (cross-ai.mjs main); cases no-second-cli-* | closed |
| T-25-02 | Repudiation | not-installed / no-model first choice | medium | mitigate | not_installed/no_model stops name the CLI; cases not-installed-first, no-model-first | closed |
| T-25-03 | Spoofing | `extractEvents` / `classifyStop` | high | mitigate | extractEvents keeps error events only; cases edge-answer-only-*, codex-item-error-ignored | closed |
| T-25-04 | Denial of service | pattern regexes | medium | mitigate | INPUT_CAP 64 KiB tail; regexes compiled once, no nested quantifiers | closed |
| T-25-05 | Information disclosure | `failed` log line, status line | high | mitigate | composed lines carry ids and labels; relayed text redacted; case sentinel-failed-line | closed |
| T-25-06 | Tampering | `--classify-only` | medium | mitigate | --classify-only JSON.parse only, before stdin and spawn; case classify-only-no-spawn | closed |
| T-25-07 | Spoofing | `--route-<cli>` | medium | mitigate | ROUTE_VALUES enum, usage exit 2; heuristic labelled router-inferred; case route-flag-bad | closed |
| T-25-08 | Denial of service | live kill | medium | mitigate | kill only the current child via currentFinalize; cases answer-only-ok, retry-notice-no-kill | closed |
| T-25-09 | Denial of service | line buffers | medium | mitigate | line relay flushes at INPUT_CAP; case live-limit-flood | closed |
| T-25-10 | Tampering | rung 2 over a changed tree | high | mitigate | rung2Gate + promptFiles; cases ladder-dirty-inside/outside, ladder-non-git | closed |
| T-25-11 | Denial of service | retry storm | medium | mitigate | clampCount 0..3, backoffS, 60 s guard; cases pure-ladder-* | closed |
| T-25-12 | Elevation of privilege | review-mode resume | high | mitigate | codex review never resumes (sameSessionArgv null); review tree change -> contract_violation | closed |
| T-25-13 | Denial of service | cooldown cycles | high | mitigate | clampCapS 14400, cooldown <= capS, cap from first_seen; cases pure-ladder-cap-* | closed |
| T-25-14 | Information disclosure | attempt and report lines | high | mitigate | logAttempt/logReport print ids, counts, times; case sentinel-evidence | closed |
| T-25-15 | Repudiation | stop without explanation | medium | mitigate | reportAndFinish logs the report on every non-ok status, signal paths included | closed |
| T-25-16 | Tampering | dogfood re-render | medium | mitigate | plan_runner_upgrade: pristine only, never downgrades, edited -> .new; atomic writes | closed |
| T-25-17 | Denial of service | re-render during a dispatch | medium | mitigate | orchestrator-only re-render; dogfood self-test recorded (25-07, 25-REVIEW fix status) | closed |
| T-25-18 | Tampering | `resolve_route` | medium | mitigate | _confirmed_quota bool-only; resolve_route returns router/unknown/None; runner re-validates | closed |
| T-25-19 | Information disclosure | tests reading the real cache | medium | mitigate | route_fn stubbed in dispatch and env-scrub tests; scratch XDG_CACHE_HOME | closed |
| T-25-20 | Elevation of privilege | post-failure re-dispatch | high | mitigate | skills forbid post-failure re-dispatch; test_quota_policy_text pins STOP_SENTENCE | closed |
| T-25-21 | Denial of service | wake loops | medium | mitigate | WAKE_RE and CronCreate one-shot pins in test_quota_policy_text | closed |
| T-25-22 | Repudiation | skill and README text | medium | mitigate | policy lists the 11 unverified rows; router-inferred advisory; text pins | closed |
| T-25-23 | Information disclosure | owner captures | high | mitigate | 25-OWNER-CAPTURES redact-first kit; C1-C7 not run (owner); key-shape scan clean | closed |
| T-25-24 | Tampering | opencode judge lane | medium | mitigate | judges dispatched --mode review; mid-run tree check -> contract_violation | closed |
| T-25-25 | Repudiation | gate and verdict claims | medium | mitigate | each verdict cites three reports; gates recorded exit=0 in 25-11-SUMMARY | closed |
| T-25-SC | Tampering | npm/pip/cargo installs | high | mitigate | node: built-ins and the stdlib only; no manifest or lock change | closed |

*Status: open · closed · open — below high threshold (non-blocking)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-25 | 26 | 26 | 0 | gsd-security-auditor (opus), read-only; runner self-test, test_quota_policy_text and test_ai_kit_spec_runner_dispatch passed |

Informational, not blocking:
- T-25-21: the wake-line pin can be evaded (25-REVIEW IN-07, open); `cron_lines` covers the two execute SKILL.md files only. The current text is clean.
- T-25-05/T-25-14: answer lines are copied to stderr after redaction (25-REVIEW IN-05, open), a channel separate from the composed lines.
- T-25-17, T-25-24: process mitigations, verified from records.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-25
