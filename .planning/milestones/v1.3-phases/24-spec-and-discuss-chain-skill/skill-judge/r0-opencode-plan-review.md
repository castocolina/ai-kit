DIGEST b4dba01851891ec0
# Skill Evaluation Report: ai-kit-gsd-spec-discuss

## Summary
- **Total Score**: 117/120 (97.5%) — Grade **A**
- **Pattern**: Process (phased workflow, checkpoints, medium-low freedom) with Tool-grade command grammar
- **Knowledge Ratio**: E:A:R ≈ 95:5:0 — essentially pure delta
- **Verdict**: A dense, battle-tested orchestrator skill; nearly every line encodes a landmine, an exact invocation, or a verified-behavior note Claude could not invent. Its only real issues are one duplicated normative passage and a few unverifiable cross-references.

Verified live: SKILL.md is 217 lines; references total 290 lines; scripts (`decide.py`, `edge_floor.py`, `phase_range.py`) exist and their argparse/status vocabularies match SKILL.md exactly (`detect`/`ladder`/`consent`, `floor`/`check` with exit 1=drift/2=fail-closed, `--roadmap`); `scripts/__pycache__` is untracked (not shipped).

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Every section is project/run-specific; only flaw is §3 restating fallback/second-opinion mechanics that `decision-table.md` (loaded mandatorily before any ladder call) already normatively covers (SKILL.md 130–140 vs decision-table.md 3–7, 23–34) |
| D2: Mindset + Procedures | 15 | 15 | "You are the decider… own reasoning is the rung that reads the actual code" (12–16, decision-table 43–45) plus exact resolver loop, exit-code semantics, prompt pre-answer table (90–94) |
| D3: Anti-Pattern Quality | 15 | 15 | Nine NEVERs, each with a non-obvious why, several incident-derived (`--assumptions` writes nothing, 183–184; `workflow.discuss_mode` crash leaves it flipped, 192–193; hand-written edge floor — "16.1–19 SPECs did" drift, 196–197) |
| D4: Specification Compliance | 15 | 15 | Name valid; description has WHAT, WHEN with three verbatim trigger utterances, keywords (jev/Laya/TypeSafe/SPEC.md/`--analyze --all --batch`), a no-backend guarantee, and a negative scope ("Not for plan-phase or execute-phase") |
| D5: Progressive Disclosure | 15 | 15 | 217-line body; four MANDATORY/conditional in-workflow triggers (59, 101, 105, 213–214) plus explicit Do-NOT-load scoping (216–217) |
| D6: Freedom Calibration | 15 | 15 | Exact commands and JSON schema where a wrong flag silently destroys work; principles where judgment is the point (neutrality, evidence-vs-model, quality rule) — correct split throughout |
| D7: Pattern Recognition | 9 | 10 | Clear Process pattern with checkpoints and commits; slight hybrid with Tool pattern and marginally over the ~200-line norm |
| D8: Practical Usability | 14 | 15 | Decision trees (which answer wins), verified CLI behavior, fail-closed paths for every missing dependency; small gaps below |

## Findings

**Critical** — none.

**Important**
1. **Duplicated normative semantics — drift risk + token waste.** SKILL.md lines 130–140 and `references/decision-table.md` lines 3–7 + 23–34 both define the forced-fallback rule (`fallback: true` with high `top` = forced, not low confidence) and the second-opinion trigger. Two normative copies in one package; when thresholds or client behavior change, one gets updated and the other silently disagrees — the loaded-first copy is the one an agent trusts most. Keep the semantics in `decision-table.md` (already a mandatory pre-ladder read) and reduce SKILL.md §3 to a one-line pointer. This is also the sole D1 deduction.

**Minor**
1. **Unverifiable case citations.** SKILL.md line 141 cites "(17 K01/K08, 18.1 T2, 23 B10/B12, 24 C13)"; grep confirms `worked-examples.md` contains only K08, T2, B12 and C08 — K01, B10 and C13 resolve nowhere in the package. Either stale IDs or evidence the reader can't inspect, in a sentence meant to build trust in remote overrides.
2. **Context-free install hint.** Line 37–38 tells the owner to run `python3 tools/setup.py install --headless --skills jev-fast-decision --replace-existing` without saying from which repo (ai-kit's checkout) — ambiguous for a message relayed mid-run in an unrelated GSD repo.
3. **Underspecified resolution source.** Line 97–98: "Omit `model` when it resolves to `inherit` or empty" never says where the resolved value is observed (presumably `init phase-op` output, named two lines later as `agent_runtime`).
4. **Description density.** The line-3 description answers WHAT/WHEN/KEYWORDS completely but is one ~160-word sentence; an agent scanning dozens of descriptions pays for the run-on structure. No rubric deduction — it satisfies every checklist item — but two sentences would scan identically at lower cost.

CURRENT 117/120
CRITICAL 0
IMPORTANT 1
