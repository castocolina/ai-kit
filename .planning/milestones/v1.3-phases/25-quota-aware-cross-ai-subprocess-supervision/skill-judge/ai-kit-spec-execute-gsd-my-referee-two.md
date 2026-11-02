# ai-kit-spec-execute-gsd — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 6, skill digest `5ec033df03ba8007`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=239s out=543577 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

All evidence gathered. Verification summary: every Phase 25 claim in SKILL.md was checked against the runner source of truth (`cross-ai.mjs`), the policy file, `runner_dispatch.py`, and the Phase 25 diff — the exit-75/69 semantics, `retry_after_s=`/`cycle=` evidence fields, route pinning, early-retry refusal, and the 4-hour cap all match.

---

# Skill Evaluation Report: ai-kit-spec-execute-gsd

**Score 109/120 (91%) — Grade A. Pattern: Process/Tool hybrid. Knowledge ratio ≈ E:80 A:15 R:5.**

## Dimension table

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 18 | 20 | Near-pure expert content: live-confirmed GSD internals (tier resolution, config-set semantics), hook expansion rules, ownership sidecar, wake choreography. Minimal redundancy. |
| D2 Mindset + Procedures | 14 | 15 | "Mindset before writing" block (resolve fresh, opt-in check, stale-hook cleanup) is real thinking-pattern transfer; domain procedures Claude could not invent. |
| D3 Anti-Pattern Quality | 14 | 15 | NEVER list with WHYs (re-resolution rewrites the hook; early retry refused without model call; skip falls back to native executor). |
| D4 Specification Compliance | 14 | 15 | Valid frontmatter; description answers WHAT/WHEN with three enumerated triggers and searchable keywords (`cross_ai_command`, `model_profile_overrides`, `/gsd-execute-phase`). Dense single sentence but complete. |
| D5 Progressive Disclosure | 13 | 15 | 499 lines (over 300 ideal, at the 500 ceiling); references gated by "read only if" and a MANDATORY-on-stop conditional trigger — good layering, heavy body. |
| D6 Freedom Calibration | 14 | 15 | Fragile ops (config writes, hook string, wake prompt) get exact scripts and exit-code tables; judgment explicitly delegated to owner. Correctly low-freedom. |
| D7 Pattern Recognition | 9 | 10 | Phased Process workflow with checkpoints (STOP per branch) plus Tool-grade exact commands — masterful fit. |
| D8 Practical Usability | 13 | 15 | Claims verified against `cross-ai.mjs`; every mode/exit/edge case has a runnable path. Dragged by findings 1–2 below. |

**Phase 25 accuracy check (the focus area):** all verified correct — one CLI per call with no fallback (policy §"One CLI per call"; runner starts first `--prefer` entry only), same-session-then-new-session ladder (`ladderNext`/rungs), router cycles across calls under the 4-hour cap (`capS` 14400, exit 69 `stopped=cap`), evidence lines on every stop (`cross-ai: attempt`/`report` + `AIKIT-XAI`), `--route-<cli> router|unknown` from catalog-confirmed `fallback_quota` with per-CLI `routerBacked` fallback, bare exit 75 for off-router/exhausted-transient stops, early-retry refusal without a model call. The policy pointer (`../ai-kit-spec-review/references/subprocess-quota-policy.md`, exists, 119 lines) is correct, and the NEVER list + wake prompt forbid self-switching harness/provider/model at every decision point.

## Findings

1. **[Minor]** `ai_kit_spec_gsd/cli.py:2-7` — module docstring enumerates 7 subcommands but the shim exposes 9; `print-dispatch-guidance` (used by SKILL.md Step 2, line 254) and `print-summary-format-block` are missing. **Fix:** sync the list with `_COMMANDS` (cli.py:459-469).

2. **[Minor]** SKILL.md:61-66 + 103 — no STOP when the sibling skill is missing: if `ai-kit-spec-review` never resolves, `$TOOLS_PY` is empty and Step 1 calls `python3 "$TOOLS_PY" cache-path`, yielding an empty `--quota-path` and silently degraded quota awareness instead of a clean exit 2. **Fix:** add a `[ ! -f "$TOOLS_PY" ]` guard mirroring the `$CURATED_PY` check at SKILL.md:256.

3. **[Minor]** SKILL.md:450-452 restates the ladder in three lines while the pointed-at policy says "A skill links here; it does not copy the rules" (subprocess-quota-policy.md:5). The paraphrase is accurate today but can drift (it already omits the bare-75 subcase for an unwritable cycle-state file, cross-ai.mjs:2476-2477). **Fix:** collapse to one line plus the existing MANDATORY pointer.

4. **[Minor]** `ai_kit_spec_gsd/gsd_cross_ai.py:12-19` — the Phase 25 `env` parameter is undocumented in the docstring (only an inline comment). **Fix:** one line: `env` enables the catalog lookup pinning `--route-<cli>`; None leaves the runner's own rule.

5. **[Minor]** SKILL.md is 499 lines — at the rubric's ceiling; the skip/retry rules are stated twice (SKILL.md:25-28 and 457-458) and "Who reads that file" (153-157) is reference-grade. **Fix:** trim duplicates or move resume-file reader semantics into `references/`.

**Top improvement:** finding 2 (silent quota degradation) is the only one with behavioral impact; the rest are hygiene. No Critical, no Important — the Phase 25 policy description, the thing most likely to drift, verifies clean against the source of truth.

DIGEST 5ec033df03ba8007
CURRENT 109/120
CRITICAL 0 IMPORTANT 0

---
Skipped: running the runner's `--self-test` and the repo test suite (read-only judge) — behavioral claims verified by reading `cross-ai.mjs`, not execution; residual risk is source/behavior divergence I couldn't observe.
