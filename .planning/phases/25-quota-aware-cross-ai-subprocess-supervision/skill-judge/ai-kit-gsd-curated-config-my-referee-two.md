# ai-kit-gsd-curated-config — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 6, skill digest `c3f432f44f2da7b7`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=267s out=382002 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

Verification complete. I read the rubric, the full skill (SKILL.md, both references, the policy it points to), the Phase 25 diff, and cross-checked the docs against the shipped code (`cross_ai.py` TEMPLATE_VERSION=7, `cross_ai_script.py` _READY_TEMPLATE=7, `plan_edit.py` `_confirmed_router`, `apply.py`/`plan_io.py` refusal path, and the template's STATUS_TABLE in `ai-kit-spec-review/references/cross-ai.mjs`).

# Skill Evaluation Report: ai-kit-gsd-curated-config

**Pattern**: Process + Navigation hybrid (exit-code decision tables, phased pipeline, routed references). **Knowledge ratio**: ~E92:A8:R0 — near-pure expert content.

**Phase 25 verification (docs vs. code)**: exit-code table matches the template's STATUS_TABLE exactly (69 terminal / 75 quota+transient / 124 / 127 not_installed / 128+N); `router_backed` rule matches `_confirmed_router` (is_router + router_confirmed + purpose `execute`, recomputed on re-pick, name-only guess excluded); template-7 readiness floor matches `_READY_TEMPLATE`; the force-immune skipped-skill refusal is in `prepare()`, so it covers both `apply` and `--dry-run` before any write; the one-CLI/no-fallback rule, evidence lines (`cross-ai: report` only on non-ok, `action=stop` even on clean exit 0), the one sanctioned exit-75 re-entry, and the "never switch harness/provider/model" rule all match the policy; both relative policy links resolve. SKILL.md correctly links the ladder instead of restating rungs. **No misdescription found.**

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | ~92% expert content (trust model, router_backed semantics, gsd-core skill resolution, template/.new invariants, per-flow permission facts); small in-file repetition |
| D2: Mindset + Procedures | 15 | 15 | "Ask yourself" pre-flight frame + non-obvious pipeline ordering, refusal→action trees, exact commands |
| D3: Anti-Pattern Quality | 15 | 15 | 9 NEVERs each with reason (incl. adversarial "just apply it" case and the runner-stop switch ban) + 9-row mistakes table |
| D4: Specification Compliance | 13 | 15 | Valid frontmatter; description has WHAT/WHEN/keywords for setup, render, ensure-runner, .new merge — but no trigger for the dispatch-stop scenario Phase 25 made load-bearing |
| D5: Progressive Disclosure | 15 | 15 | Scenario-detected MANDATORY triggers with precise disambiguation ("action=stop alone says nothing") + "Do NOT load" in runner.md; links verified |
| D6: Freedom Calibration | 15 | 15 | Low freedom where fragile (verbatim obligations, fingerprint-bound approval, JSON-vs-bare values), user judgment where appropriate |
| D7: Pattern Recognition | 9 | 10 | Masterful Process/Navigation fit; 405 lines vs ~200 Process norm, justified but dense |
| D8: Practical Usability | 14 | 15 | Verified consistent with code and policy; one re-entry-actor ambiguity |
| **Total** | **115** | **120** | 95.8% — Grade A |

## Findings

1. **Important (D4)** — `skills/ai-kit-gsd-curated-config/SKILL.md:3` — the description's triggers cover setup/lifecycle ("configure", "render cross-ai.mjs", "ensure-runner", "merge a cross-ai.mjs.new") but never the dispatch-stop scenario the body now owns (the MANDATORY policy read at SKILL.md:221-226, the verbatim-evidence rule at 244-249, NEVER #9 at 378-380). An agent facing `AIKIT-XAI status=no_change` / exit 75 has no activation-time signal to load this skill. **Fix**: extend the description's use-when list with e.g. "or when a cross-ai.mjs dispatch stops (an `AIKIT-XAI status=` other than `ok`, exit 69/75/124/127)". (Sibling `ai-kit-spec-execute-gsd`'s description doesn't cover it either, so the gap is real.)
2. **Minor (D8)** — `SKILL.md:224-226` vs `SKILL.md:244` — "The one sanctioned re-entry is the one-shot after an exit 75…" sits next to "This skill never dispatches a model call", leaving it ambiguous whether this skill may itself perform the one-shot re-invocation (a model call through the runner) or only the owner may. **Fix**: one clause stating the actor, e.g. "the one-shot re-entry is itself a live dispatch — perform it only when the user's ask covers it; this skill schedules nothing on its own."
3. **Minor (D5)** — `references/runner.md:43-49` partially copies the policy's knob clamps and the `attemptTimeoutS` rung nuance (`subprocess-quota-policy.md:20-21, 71-81`) although the policy says "a skill links here; it does not copy the rules." Consistent today, but two copies drift. **Fix**: keep only the CONFIG knob names + curated-config-relevant notes (e.g. "only a set value leaves a timed-out attempt room for a retry rung" if you want the callout) and link the clamps.
4. **Minor (D1)** — `SKILL.md:271-272`, `:354`, `:375-377` — the ".new is not active / check the active file's line-2 `template=` header" invariant is stated three times in SKILL.md (plus runner.md). It's safety-critical, so the NEVER entry should stay; the other two repeats could collapse into one. **Fix**: keep the NEVER entry as the recall layer, drop the duplicate sentence from the subcommand table or the Cross-AI section.

No Critical findings: every Phase 25 claim I tested (one CLI per call, no fallback, ladder pointer, router_backed authorization, evidence-line rules, never-switch rule) matches the shipped code and the policy.

Ponytail: skipped the evals/ files and v1 subcommand behavior (not pointed at by the Phase 25 diff); scores assume the sibling skills' own docs are accurate where this skill defers to them.
