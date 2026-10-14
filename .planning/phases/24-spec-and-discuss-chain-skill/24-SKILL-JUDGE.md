# Phase 24 — skill-judge gate: `skills/ai-kit-gsd-spec-discuss/`

**Date:** 2026-10-14
**Why:** a new SKILL.md (AGENTS.md: any new SKILL.md passes `/skill-judge`). The pass bar is no
remaining Critical or Important finding, or a score of at least 96/120.
**Baseline:** none (new skill).
**Reviewer:** the authoring session (Claude Opus 5.5), applying the skill-judge rubric. This is
a self-evaluation, so the scores are deliberately conservative. A cross-AI re-run in code review
is still owed (see the user memory note on skill-judge in code review).

## Summary

- **Total score:** 106/120 (88%), grade B. This passes the bar, which requires either ≥ 96 or
  no Critical/Important finding; both hold.
- **Pattern:** Process (set-up, spec, discuss, ladder, ledger), with Tool-level scripts for the
  fragile steps.
- **Knowledge ratio (E:A:R):** about 75:20:5.
- **Critical / Important findings:** 0 / 0, after the fixes below.

## Dimension scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1 Knowledge Delta | 17 | 20 | Live-verified landmines: literal `--assumptions` writes nothing, discuss `--auto` chains into plan-phase, Laya context bleed and run-to-run drift, the floor depends on exact requirement text, `config-get` "Key not found", `discuss_mode` leaks to other commands. §0's set-up steps are partly activation content |
| D2 Mindset + Procedures | 13 | 15 | Opening "you are the decider" frame plus non-obvious ordering (ladder before "Yes, proceed"; amendments in the later phase's commit; STATE in its own commit) |
| D3 Anti-Patterns | 14 | 15 | Nine NEVERs, each with the failure it causes |
| D4 Specification | 14 | 15 | Valid frontmatter (YAML-parsed); WHAT, WHEN, quoted trigger phrases and keywords in 824 characters; the first 200 characters still say what it chains |
| D5 Progressive Disclosure | 14 | 15 | 199-line body; four references with MANDATORY triggers inside the steps, a conditional trigger for the examples, and a "Do NOT load" rule |
| D6 Freedom Calibration | 14 | 15 | Detection, consent, payload guard, range and edge floor are scripts (low freedom); the decisions themselves stay prose with a decision table (medium) |
| D7 Pattern | 9 | 10 | A clean Process pattern near its ~200-line norm |
| D8 Usability | 11 | 15 | Fallbacks are covered (no gsd-core, no subagents, no backend, engine missing, malformed item). Not yet run end to end as a skill on a fixture project: the scripts are tested and `decide.py` was run live against Laya and TypeSafe, but the full chain was only exercised by hand in this milestone |

## Findings

- **Important (fixed in this gate):** §0 had no command to resolve the scripts dir. Added the
  candidate-loop snippet, tested from the checkout.
- **Important (fixed in this gate):** nothing said what to do when `edge_floor.py` exits 2.
  Added "fail closed: stop the spec step, never write the table by hand".
- **Minor (fixed in this gate):** `phase_range.py` gives a false-positive "SPEC newer" after a
  later phase's cross-phase amendment (live: 16.1, amended by Phase 17's commit). Added the
  `git log` check.
- **Minor (open):** D8 — the SPEC R3/R4 "dry-run transcript on a fixture project" acceptance
  is not produced yet; the first real use of the skill should record it.

## Evidence

- `python3 -m unittest tests.test_ai_kit_gsd_spec_discuss`: 33 tests, OK.
- `decide.py` live (scratch `XDG_CONFIG_HOME`): Laya decided 2 of 3 items, TypeSafe took the
  fallback item, the both-low item came back `own_reasoning`; no key in output.
- `edge_floor.py check` over this milestone's SPECs: 20–24 pass; 22 and 23 were corrected in
  this commit (their amended requirement text changed the floor); 16.1–19 drift (floors computed
  earlier with a truncating prototype extractor) and are ledgered for regeneration before their
  planning.
