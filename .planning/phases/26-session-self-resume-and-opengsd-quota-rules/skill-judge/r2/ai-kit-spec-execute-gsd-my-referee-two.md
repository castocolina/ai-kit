Judge: my-referee-two
Reviewed-sha256: 8cef3656bbba9bfa154bbdb15d0361b359afc2e99b349e069b4e8405506056b2
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=571s out=343821 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 109
Critical: 0
Important: 2

# Skill Evaluation Report: ai-kit-spec-execute-gsd

**Grade: A (90.8%)** · Pattern: Process (phased workflow, checkpoints, STOP gates) · Knowledge ratio E:A:R ≈ 90:8:2 · Layer 2 = 459 lines; references 77 + 63 lines; scripts (`ai-kit-spec-gsd.py` + `ai_kit_spec_gsd/`) verified present.

**Verdict:** A dense, near-pure knowledge-delta orchestration skill whose every checkable factual claim verifies against the repository; its cost is extreme sentence density and one sanctioned-but-unrouted decision path.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Mode/exit-code/ownership/wake contracts are all expert-only; no tutorials or generic advice |
| D2: Mindset + Procedures | 14 | 15 | "Mindset before writing" (SKILL.md:200-206) + non-obvious ordering (opt-in check before *any* write incl. `ensure-runner`; cleanup even when this run isn't cross-AI) |
| D3: Anti-Pattern Quality | 15 | 15 | 9-item NEVER list, each with a hard-won reason (e.g. never re-resolve: a fresh `resolve-dispatch` rewrites the hook, SKILL.md:20-24) |
| D4: Spec Compliance | 14 | 15 | Valid name; description has WHAT + 3 explicit WHEN triggers + keywords; a single ~840-char sentence chain |
| D5: Progressive Disclosure | 13 | 15 | MANDATORY trigger embedded in workflow (231-235); explicit "not needed to execute" on dispatch-notes.md:3; body is 459 dense lines with deliberate redundancy vs the NEVER list |
| D6: Freedom Calibration | 14 | 15 | Exact scripts for fragile config writes; owner gates at every judgment point; honest "unverified" labels |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern; heavier than canonical |
| D8: Practical Usability | 11 | 15 | Internally consistent, blocks match the CLI exactly; density and one unrouted branch cost points |

## Factual claims checked against the repository (all verified)

- Shim exists and delegates as described: `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py:18`.
- All 7 subcommands and every flag used (`--quota-path`, `--set KEY=JSON`, `--min KEY=INT`, `--key`, `--target-dir`, `--phase-file`, `--state-json`, `--runtime/--model`): `ai_kit_spec_gsd/cli.py:448-505`.
- Exit semantics: `ConfigError` → 2 (`cli.py:537-539`); `write_failed` → 1 with JSON (`cli.py:186`); reverse-order revert + `revert_failed` (`gsd_config.py:109-149`); ownership sidecar makes `clear` a no-op unless adapter-owned (`gsd_config.py:76-106`).
- `ai-kit: gsd-core <version> at <path>` stderr banner: `cli.py:110`. gsd-core search order `<root>/gsd-core`, `.claude/gsd-core`, `.codex/gsd-core`, then host homes: `ai_kit_spec/gsd_tools.py:5,92-93`.
- Hook-token allowlist exactly `letters, digits and ._:/@+=,#-`: `HOOK_TOKEN_RE` at `ai_kit_spec/runner_dispatch.py:36`.
- All fallback reasons + provenance values: `adapter.py:240-313,164-196`; `malformed_config` `cli.py:121`. "ignoring untrusted project-local config": `config_io.py:410`. `purpose="execute"` that can't execute → exit-2 config error: `execute_selection.py:75-108`.
- `claude` review-only (`detection.py:114`), grok row (`:119`), claude aliases sonnet/opus/haiku/fable (`:113`), probe_codegraph 15 s report-only with install-command relay (`:1203-1266`), sync-then-init (`:1313-1323`).
- Siblings: `cache-path`/`trust-local` exist (`ai_kit_spec/cli.py:142,266`); cross-AI §4/§6-§8 exist and match the stop rules, whole-minute/under-60 s in §6 (`ai-kit-cross-ai/SKILL.md:75-172`); session-wake `arm --host/--session-id/--ref` valid on every subparser (`ai_kit_session_wake/cli.py:69-82`); ensure-runner 0/1/2 + `.new` (curated-config `SKILL.md:352`) and `MIN_TIMEOUT_S = 1800` (`ai_kit_gsd_curated_config/cross_ai.py:47`).
- `*-PLAN.md` sibling convention: real in this repo's own GSD planning (`.planning/phases/20-live-validation-on-codex-opencode/20-01-PLAN.md` … `20-07-PLAN.md`); `.planning/scripts/cross-ai.mjs` exists.

**Unverifiable here** (no gsd-core/`gsd-tools.cjs` anywhere in this repo): the bare `${CROSS_AI_CMD}` word-split expansion, Node 24 floor, GSD's `cross_ai_execution` delegation gate, dirty-tree warning, `.claude/commands/gsd-execute-phase.md` convention. No deduction taken for these; the risky one is guarded (see finding 3).

## Findings

1. **Important — SKILL.md:274-277, 311-313; references/cross-ai-hook-setup.md:62-64.** The owner-approved native fallback is sanctioned ("reached only after the owner explicitly chose native execution"; "Continue only when the owner explicitly says to run this phase natively") but no step ever routes it: after the owner's yes, the agent must guess whether to re-run Step 1 (the natural reading of every other resume instruction, and the action the NEVER at :20-24 warns can rewrite the hook) or jump straight to Step 3 with the captured `fallback_notice` literal. **Fix:** one sentence at SKILL.md:277 — "On an explicit owner decision to run natively, do not re-run Step 1/2; continue at Step 3 with the captured `RESULT_MODE=fallback_notice` literal and `--runtime` omitted" — mirrored in cross-ai-hook-setup.md:64.
2. **Important — SKILL.md:20-24, 216-221, 405-408, 421-425.** Sentence density at the exact points an agent must act: one 74-word NEVER bullet stacking the re-resolve ban, the wake re-entry rule and the trust-local exception (:20-24); an 86-word sentence covering pin scope, hook ownership, plan opt-in, owner ask and stop (:216-221); the CronCreate paragraph nesting wake text, session lifetime and post-session handoff (:421-425). The content is right; the packaging is the most likely source of a misparse in live use. **Fix:** split each into rule → exception → reason (2-3 short sentences or a mini list), adding no new length.
3. *Minor — references/dispatch-notes.md:11-15.* GSD's bare-expansion semantics are stated as fact, but gsd-core is absent from this repo and the adapter's own banner exists because that contract can drift (`ai_kit_spec_gsd/cli.py:96`). Harmless in effect — `runner_dispatch.py:36` blocks unsafe tokens before they ever reach the hook — but it should carry a "reverse-engineered from gsd-core <version>, allowlist-guarded" label per the repo's own certainty rule. **Fix:** one provenance clause.
4. *Minor — SKILL.md:365 vs :417.* The initial arm passes `--ref "$CWD/.planning/STATE.md"`; the stop re-arm passes only `--ref "$RESUME_STATE_PATH"`, and `--ref` is a per-call list (session-wake `SKILL.md:70`), so the STATE.md ref is dropped on re-arm. **Fix:** repeat both `--ref` flags at the re-arm.
5. *Minor — SKILL.md:357.* The `*-PLAN.md` glob matches this repo's GSD layout but is silently 0 on any project whose plan naming differs, disarming the wake with no signal (the skill accepts that: "Never fail the run on the wake"). **Fix:** one clause naming the assumed convention so a mismatch is diagnosable.
6. *Minor — SKILL.md:399-441.* Step 3's stop handling restates the NEVER list (:26-28) and cross-AI §6-7. Deliberate safety redundancy, but it is the largest token cost in an otherwise lean body; a pointer plus the deltas would shave ~30 lines.

**Top 3 improvements:** findings 1, 2, then 4.

---
Not checked: gsd-core itself (absent from this repo) and any live execution of the bash blocks — all verification was static (files named by the package). Risk: findings 1-2 are usability judgments; a maintainer who values the fail-safe redundancy may accept them.
