Judge: my-referee-two
Reviewed-sha256: 06ef499ae59c57f92188a9ec3fb8005423d08d836e3a9264f0f476c404604eeb
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=303s out=163845 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-project-rules-agents

**Grade: A (92%)** · Pattern: Tool (exact CLI + payload contracts) with a Process hand-off · Knowledge ratio E:A:R ≈ 88:12:0 · Self-contained, 106 lines, no references dir. Verdict: a rare skill whose every factual claim I could check against the repository is true; the remaining findings are polish.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Payload contracts, import-vs-lookup distinction, exactly-once rationale — all expert-only; zero tutorial filler |
| D2: Mindset + Procedures | 14 | 15 | Non-obvious ordering (confirm near-misses before the single refactor invocation); "a successful path lookup is not proof the import will succeed" |
| D3: Anti-Pattern Quality | 14 | 15 | Five specific NEVERs, each with a mechanism-level WHY, each verified against code |
| D4: Specification Compliance | 14 | 15 | WHAT + WHEN + quoted-utterance trigger + honest scoping; final clause is a double-parse |
| D5: Progressive Disclosure | 14 | 15 | 106 lines; defers rule text to `rules.py` instead of restating it |
| D6: Freedom Calibration | 14 | 15 | Exact commands where fragile, user gates, verbatim protection; freedom only in phrasing and host mechanism |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern; Steps A/B/C are a disciplined process hand-off |
| D8: Practical Usability | 12 | 15 | Executable end-to-end with host fallbacks; small flow/edge gaps below |

## Claims verified against the repository

- 20 rules R01–R20 with id/category/criticality/condition/signals/summary — `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:49-305`.
- `verbatim: true` on exactly R18/R19/R20 — rules.py:278, 292, 303 (SKILL.md:61 ✓).
- R20 per-stack clause from `ai_kit_rules_common.tool_catalog.PARALLEL_TEST_FORMS` — rules.py:301; `skills/_shared/ai_kit_rules_common/tool_catalog.py:757` (SKILL.md:106 ✓).
- `check` returns `{"workflow", "links"}` — `ai_kit_project_rules_agents/cli.py:196`; link parsing strips `#`/`?`, skips anchor-only/absolute/scheme targets (cli.py:44-47), image links match the unanchored regex (cli.py:22); `remediate` runs `check` internally (cli.py:209-217).
- `remediate` payload `{"remediate","blocked","notices"}`, `auto_apply` true only for `missing`, notices carry `reason`, `verbatim` carried forward — `skills/_shared/ai_kit_rules_common/remediation.py:104-116, 89-100, 35, 145`. `blocked` always empty here: `check()` emits only workflow+links and `build_remediation` fills `blocked` solely from STRUCTURAL_KINDS (remediation.py:31, 118-142) — SKILL.md:37 ✓.
- Literal lowercase substring classification and the ≥50% (ceil(n/2)) flat threshold — `skills/_shared/ai_kit_rules_common/classification.py:110-117, 282, 317` (SKILL.md:67-74 ✓, attribution caveat in finding 2).
- Signals-not-category routing, incl. R02 ("makefile" category, non-empty signals) — classification.py:311-322; rules.py:63-70 (SKILL.md:88-94 ✓).
- Copy-install ImportError by design, symlink/checkout-only import — `ai_kit_project_rules_agents/__init__.py` (raises with that exact rationale); symlink install in `tools/setup.py:1082-1083, 1269-1295` (SKILL.md:28 ✓).
- R18/R19 `unverified` → notices — classification.py:48-53, 63-74 → remediation.py:89-101 (SKILL.md:37 ✓).
- Trust note: probe only when `.planning/` exists, runs gsd-tools `runtime-identity`, path printed on stderr — cli.py:169-175; `skills/_shared/ai_kit_rules_common/gsd_identity.py:103-107` (SKILL.md:98 ✓).
- `/agent-md-refactor` five phases / no CLI / user-confirmation gate — not in this repo; corroborated as directly-verified ground truth in `.planning/milestones/v1.1-phases/06-agents-md-rules-checker-skill/06-02-PLAN.md:309`. Not independently checkable within this review's read scope.

## Findings (all minor)

1. **Minor — SKILL.md:44-45.** The example payload shows `R05` with `"criticality": 2`, but R05 is `CRITICALITY_MEDIUM = 3` (rules.py:38, 105-109); criticality 2 is R03 (rules.py:80). Fix: change the example id to R03 (or the value to 3) so the "real-looking" example matches the source of truth.
2. **Minor — SKILL.md:67-73.** Attributes the engine to `rule_checker.py`; the matching/threshold code lives in `ai_kit_rules_common/classification.py` (rule_checker.py:6-9 says so itself). Also "≥50%-of-signals" exactly describes flat 3-signal rules only; grouped rules (R04/R19, classification.py:120-134) require every group, and R20 uses per-stack rows. Harmless in effect (R19 is verbatim-inserted anyway; under-matching yields a false near-miss, which Step A's confirmation catches). Fix: name classification.py and scope the threshold sentence to flat signals.
3. **Minor — SKILL.md:30-37.** The flow never states that `check` must be run to surface `links`: `build_remediation` reads only `workflow` + STRUCTURAL_KINDS and silently drops the `links` key (remediation.py:87-145; cli.py:196). An agent that runs only `remediate` (it "runs `check` internally", SKILL.md:37) never sees broken links. Fix: one sentence — "Run `check` as well when you want link findings; `remediate`'s payload drops them."
4. **Minor — SKILL.md:17-23.** The resolver's candidate list omits the `<pi_dir>/skills` symlink mirror this repo's own installer creates (tools/setup.py:45, 1680-1715); on a selective pi-only install the loop prints nothing and the agent reports "not installed" though an importable symlinked copy exists. Fix: add the pi dir to the candidate list or note the limitation.
5. **Minor — SKILL.md:59, 102.** "(D-05)" is an internal decision-record id with no in-file key; an executing agent outside this repo cannot resolve it (the code's D-06/D-07/D-33/D-34 references share the problem but are comments, not agent-facing instructions). Fix: drop the parenthetical or expand it to one plain clause.
6. **Minor — SKILL.md:30-37.** No guidance for a target repo whose root instruction file does not exist: `_resolve` falls back to an empty text (cli.py:137-150), so every always-condition rule reports `missing` and the flow would hand ~20 inserts to `/agent-md-refactor` against a file that isn't there. Fix: one line — "if no root instruction file exists, stop and report instead of remediating."

## Top 3 improvements
1. Add the "run `check` too for links" sentence (finding 3) — it is the only path where a documented feature can be silently lost.
2. Correct the example's R05 criticality (finding 1) — the example is the only payload shape an agent sees before running.
3. Cover the missing-root-file edge (finding 6) — it is the most realistic unhandled input for a "check my AGENTS.md" skill.

Ponytail note: I did not read the live `~/.claude/skills/agent-md-refactor/SKILL.md` (outside the stated read scope) — its five-phase shape rests on the repo's own planning record, so that one claim is corroborated, not independently verified.
