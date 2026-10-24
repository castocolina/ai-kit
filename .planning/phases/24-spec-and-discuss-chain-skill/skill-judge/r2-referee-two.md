DIGEST 4ce07543b1aafd75
# Skill Evaluation Report: ai-kit-gsd-spec-discuss

## Summary
- **Total Score**: 111/120 (92.5%) — **Grade A**
- **Pattern**: Process (~240 lines, phased workflow, checkpoints) with Tool-pattern decision tables correctly pushed into `references/`
- **Knowledge Ratio**: E:A:R ≈ 88:10:2
- **Verdict**: A compressed operator's brain from a real multi-phase run — nearly every paragraph is landmine-derived expert knowledge; the one real defect is an over-long description that exceeds the spec's 1024-char cap.

## Dimension Scores

| Dimension | Score | Max | Evidence |
|-----------|-------|-----|----------|
| D1: Knowledge Delta | 19 | 20 | Flag traps (98–101), Laya non-determinism with real numbers (159–162), SPEC-newer false positive (47–51); only brief activation content (81–82) |
| D2: Mindset + Procedures | 14 | 15 | "You are the decider" mindset (14–18) + unknowable domain procedures (§0–§2); §0 leans mechanical |
| D3: Anti-Pattern Quality | 14 | 15 | Nine NEVERs each naming its failure mode (203–222); in-body anti-patterns ("labelling best echoes your framing", 158) |
| D4: Specification Compliance | 13 | 15 | WHAT/WHEN/keywords/negative scope all present, but description measures **1173 chars** (line 3) |
| D5: Progressive Disclosure | 14 | 15 | 241 lines; MANDATORY triggers at decision points (72, 118, 122); Do-NOT-load (240–241); one soft trigger (84) |
| D6: Freedom Calibration | 14 | 15 | Exact commands for fragile paths, principles for judgment (§5, 158); §7 coupling criterion loose |
| D7: Pattern Recognition | 9 | 10 | Process pattern well applied; Tool-pattern decision tree kept in `decision-table.md` |
| D8: Practical Usability | 14 | 15 | Walkable ordered table, fail-closed error paths, host-gap fallbacks; script claims verified live (below) |

## Findings

### Critical (0)
None.

### Important (1)
- **I1 — SKILL.md:3 (description, 1173 chars measured)**: exceeds the Agent Skills spec's 1024-character description cap — a genuine format violation for a repo that declares conformance to the open standard. Compounding it, roughly the first two-thirds is operational detail (config-get keys, `yolo`/`mvp_mode` recommendation logic) duplicated nearly verbatim in §0 step 7 (lines 64–70), spending always-in-memory Layer-1 tokens on body content. Fix: keep WHAT/WHEN/trigger-phrases/negative scope in the description (~400 chars); the mechanics already live in §0.

### Minor (6)
- **M1 — SKILL.md:84**: the `log-formats.md` trigger at the Interview Log decision point is a parenthetical "(format: …)" rather than the MANDATORY framing used at lines 72/118/122 — an agent can write a committed SPEC Interview Log without loading the format spec (whose column/cell rules are non-trivial).
- **M2 — SKILL.md:110**: "todos → fold those scoring ≥ 0.4" — the threshold has no sourcing (workflow constant vs. this skill's invention); an executor can't tell whether to re-derive it.
- **M3 — SKILL.md:197–199**: §7 gates background overlap on "coupling is low" but gives no criteria for judging coupling (contrast the analyzer-brief's coupling block, which asks the analyzer to report it).
- **M4 — SKILL.md:30–31, 39–40**: external file pointers (gsd-core's `references/gsd-run-resolver.md`, the client's `reference.md`/`backends/`) are resolvable only implicitly through the scripts; a doc-only reader can't mechanically locate them. Informational-only, since `decide.py` handles the real path.
- **M5 — SKILL.md:113–114**: `init.phase-op` appears bare, without the `gsd_run query …` command form shown for it (unlike `phase.mvp-mode` at line 61).
- **M6 — `scripts/__pycache__/*.pyc`**: compiled bytecode shipped in the skill package (stale-bytecode risk on distribution). Outside the reviewed SKILL.md + references/ scope, but visible in the package.

## Verification notes
- Description content counted programmatically: 1173 characters (I1's basis).
- Every command claim cross-checked against the three scripts' argparse: `decide.py` has `detect` / `ladder --second-opinion` / `consent grant|revoke|show`; `edge_floor.py` has `floor|check <spec>`; `phase_range.py` has `--roadmap/--from/--to/--list` — all match SKILL.md exactly.
- The decision table was mentally traced: `decision-table.md` rows 1/3/5 resolve `worked-examples.md` cases 3/1–2/3 correctly, including the forced-`fb` and no-high-remote branches.
- Per the repo's completion gate (no Critical/Important finding **or** score ≥ 96/120): 111 passes on the score arm; I1 should still be fixed.

Top fixes, in order: I1 (trim description to ≤1024 chars), M1 (harden the line-84 trigger to MANDATORY), M2 (source the 0.4 constant).

Not checked: script *behavior* beyond argparse interfaces (the user scoped the judgment to SKILL.md + references/), and no baseline score exists to compare regression against.

CURRENT 111/120
CRITICAL 0
IMPORTANT 1
