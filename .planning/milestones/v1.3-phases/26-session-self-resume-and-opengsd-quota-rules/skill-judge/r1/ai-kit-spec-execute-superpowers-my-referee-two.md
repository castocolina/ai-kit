Judge: my-referee-two
Reviewed-sha256: 14d9f06f85826c766e6865b7161e3eae5fc6cc20d6938a87ddcad79e9073f35a
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=498s out=424903 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 107
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 107/120 (89%) — Grade **B**
- **Pattern**: Process (phased Step 0–4 workflow) with Tool-style decision trees embedded at each branch
- **Knowledge Ratio**: E:A:R ≈ 90:10:0 — almost pure knowledge delta
- **Verdict**: An unusually rigorous operational skill whose every checkable factual claim survived verification against the repository's code; the one real defect is a needless hard dependency on `rg` in the status-parsing line, plus a few robustness warts.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Three-set exclusion state machine, resume semantics, mode-shape guards, exit-code lattice, escalation-anchor floor — none of it model prior knowledge; zero tutorial filler |
| D2: Mindset + Procedures | 14 | 15 | "Permanent or same-wave?" thinking prompt (SKILL.md:143-145) plus exact, non-obvious ordering (relay evidence before folding; increment `$FIX_ROUND` before the check) |
| D3: Anti-Pattern Quality | 14 | 15 | Nine-item NEVER index with non-obvious WHYs (runtime-id-excludes-nothing; quota mislabel "retries a broken candidate forever or locks out a recovered one") |
| D4: Specification Compliance | 13 | 15 | Valid frontmatter; ~690-char description with WHAT/WHEN/keywords/negative scope ("not for superpowers:executing-plans…"); deduction for density — the trigger discriminator is buried mid-sentence in a wall of text |
| D5: Progressive Disclosure | 12 | 15 | MANDATORY read triggers embedded at exact workflow points, do-not-load gating for design-notes; but SKILL.md is 521 lines, over the <500 Layer-2 guidance |
| D6: Freedom Calibration | 14 | 15 | Exact bash for fragile state writes, STOP-and-ask reserved for the owner, honest uncertainty flags (unverified `.git` sandbox writes, open pi live verification) |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern, appropriate for a multi-step integration |
| D8: Practical Usability | 12 | 15 | Every multi-path point has a branch; fallbacks for scheduler-less hosts; deductions for the `rg` defect and the exit-2 parse wart |

## Critical Issues
None. No claim I could check against the repository was contradicted.

## Findings

1. **Important — SKILL.md:352 (with design-notes.md:73-74)** — The status extraction pipeline depends on `rg`: `STATUS="$(printf '%s\n' "$STATUS_LINE" | rg -o '\b(...)\b' | tail -1)"`. On a host without `rg`, this yields an empty `$STATUS`, and SKILL.md:355-356 explicitly instructs "treat it as `BLOCKED`, and do not scan `$REPORT_FILE` for one" — a successful `DONE` dispatch is then misclassified as BLOCKED and stops the wave. design-notes.md:73-74 justifies this with "tool detection already confirms it on every supported environment", which the repo contradicts: `detect_tool_availability` only `which`-checks `rg` among optional tools (detection.py:1133), and this repo's AGENTS.md describes `rg` as part of an optional local tooling layer ("may layer extra CLI tooling over the defaults"). For a skill that otherwise engineers around every host assumption (Step 0's five install shapes, the CronCreate print fallback, the `Agent`-tool portability note at SKILL.md:45-47), this one line is an inconsistency. **Fix**: use `grep -oE '\b(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)\b'` (identical semantics, POSIX-guaranteed) or add an `rg`-absence guard, and correct the design note's justification.

2. **Minor — SKILL.md:160-165 vs 171-173** — The Step 2 block unconditionally parses `INJECTION_MODE` out of `$INJECTION_JSON`, but the documented exit-2 case is "empty `$INJECTION_JSON`": on exit 2 the `json.loads` line raises a traceback before the agent reaches the STOP-and-relay instruction. Recoverable (the failure is visible), but the block should capture `$?` and branch instead of breaking. Fix: wrap the mode extraction in a `[ -n "$INJECTION_JSON" ] ||` guard.

3. **Minor — SKILL.md:263 and 425** — `$DISPATCH_BASE` is minted once under `mktemp -d`, then reused verbatim by the quota-wake prompt across a wait that can be hours (hard-tier waits default 600/900/1800 s and the lane cap is 4 h — subprocess-quota-policy.md:103-107). If the tmp dir is cleaned in between, the re-dispatch's writes fail and route as `real_error`. Fix: re-derive `$DISPATCH_BASE` in the wake prompt when its directory is gone.

4. **Minor — SKILL.md (whole file, 521 lines)** — Marginally over the <500-line Layer-2 guidance; the fenced quota-wake prompt (SKILL.md:422-437) and the two long exit-code paragraphs could move to a reference without losing the operational core.

5. **Minor (observation) — SKILL.md:96-100, 282-299, 347, 504-505; design-notes.md:42-49; escalation.md:20** — The skill's integration backbone quotes the external `superpowers:subagent-driven-development` skill ("1. Dispatch the implementer", "2. Handle the report", implementer-prompt.md, `scripts/task-brief`, "Rulings, not stalls", rounds 1–5, "MORE CAPABLE model", ledger). That plugin is not in this repository, so these claims are unverifiable here; no in-repo text contradicts them, and cli.py:385-386 (adapter help text) echoes `scripts/task-brief` consistently. Same for `Agent`-tool/`CronCreate` behavior claims.

## Claims Checked Against the Repository (all verified)

- Subcommands, flags, and "`--heartbeat-interval` is required but unused" — `ai_kit_spec_superpowers/cli.py:381-456` (parsed at 420, never read) and 344-353.
- Exit 2 on malformed config / purpose="execute" custom, grok, or claude entries — `ai_kit_spec/cli.py` review side `ConfigError`→2 in adapter cli.py:477-484; `execute_selection.py:74-108` + adapter cli.py:156-160.
- Mode shapes: `quota_exhausted`/`no_candidate` carry no `key`/`runtime`; native/external_cli field sets incl. `effort`/`service_tier`; `ladder_keys` in every mode — adapter cli.py:129-148, 190-199, 252; `dispatch_injection.py:294-307`.
- `no_usable_dispatch` fallback and merged-reason recoverability — adapter cli.py:132-139.
- Reason vocabulary (`quota`…`real_error`, `billing_or_access`, `capacity`, `git_timeout`, route names) — `error_classifier.py:16-25, 35-39`; `routing.py:36`.
- `classify-dispatch-failure` ok/quota/real_error lattice, exit-75 whole-number gate, exit 69/75 transient/quota, nested `status` tokens — `dispatch_injection.py:398-430`.
- `resume-exclusions` drops `"quota"` keys — `dispatch_injection.py:148-162`.
- `timeout_tiers` not carried onto candidates and `resolve_timeout_tiers` unwired — `dispatch_injection.py:165-189`; `config_io.py:643-650`; adapter cli.py:25 imports only `ConfigError`.
- claude review-only in exec mode, session-default native, only-claude native selectors (fable/opus/sonnet/haiku) — `routing.py:135-179`; `detection.py:113-114, 133`.
- "ignoring untrusted project-local config", `trust-local --show`, `cache-path --kind quota` — `config_io.py:410`; review `cli.py:142-143, 266-269`.
- Evidence lines (`cross-ai: report/upstream/state`, `cross-ai: lane stopped=`, `AIKIT-XAI`), exit table, one-shot wait, whole-minute rounding, under-60 s case, "never switch" — `ai-kit-cross-ai/SKILL.md:82-94, 103-120, 128-156, 168-172`; runner template `cross-ai.mjs:3934`; `<objective>`-only digest `cross-ai.mjs:3265`; `<files>` parsing `cross-ai.mjs:4312-4317`.
- `hard_waits_s` configurable, 4-hour cap (14400), defaults 600/900/1800 — `subprocess-quota-policy.md:62-108`; 1800 s runner floor — `ai_kit_gsd_curated_config/cross_ai.py:47`.
- "subprocess dispatch needs Node" message — `runner_dispatch.py:66`.
- Session wake: `armed <host>-<id>`/`refreshed`, exit 2 refusal, exit 3, `done --host --session-id` — `ai-kit-session-wake/SKILL.md:57-65, 99`; `arm.py:187, 480, 557`.
- Codex `--sandbox workspace-write` — `execute_dispatch.py:12, 75`; report-file preservation and marker-line fallback — adapter cli.py:61-64, 274-341; result keys `stdout`/`returncode`/`reason`/`status` — `execute_dispatch.py:148-152`.
- Description trigger path `docs/superpowers/plans/*.md` exists, and `ai-kit-spec-execute` routes superpowers plans to this skill — `skills/ai-kit-spec-execute/SKILL.md:59, 65`.

## Top 3 Improvements
1. Replace `rg` with `grep -oE` in SKILL.md:352 (and fix the design-notes justification) — closes the only Important finding.
2. Guard the Step 2 block against an empty `$INJECTION_JSON` before parsing mode.
3. Re-derive `$DISPATCH_BASE` in the wake prompt if the mktemp dir has been cleaned.

---
Skipped: live execution of any shim subcommand (read-only mandate) and the external superpowers plugin files (not in this repo) — those quoted internals remain taken on trust. Main residual risk: claims pinned to the external plugin could drift if `subagent-driven-development` changes.
