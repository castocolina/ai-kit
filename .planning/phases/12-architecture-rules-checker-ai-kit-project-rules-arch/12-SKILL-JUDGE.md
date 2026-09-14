# 12-03 Task 2: `/skill-judge` evidence

Date: 2026-09-14

JUDGED_PATH: skills/ai-kit-project-rules-arch/SKILL.md
JUDGED_COMMIT: 405c50258cff848b6f835492dc7a88504fa82602
BASELINE: none (new skill, no prior SKILL.md -- verified by history search, see below)
SCORE: 100/120
CRITICAL: 0
IMPORTANT: 0
FIX_ITERATIONS_USED: 0/3

## Method

This is a brand-new skill: no `SKILL.md` existed for `ai-kit-project-rules-arch` before Task 1 of
this plan wrote one. There is nothing to regress against. No synthetic baseline was constructed,
no sibling skill's score (`ai-kit-project-rules-precommit` 103/120, `ai-kit-project-rules-makefile`
103/120, `ai-kit-project-rules-agents` 102/120) is reused as a stand-in, and the design spec's own
historical figures for a different skill are not cited as if they applied here. The pass bar is
therefore absolute rather than comparative: zero Critical and zero Important findings, or a score
of at least 96/120.

Performed by this executor, running the installed `/skill-judge` skill's rubric, against
`skills/ai-kit-project-rules-arch/SKILL.md` at its committed path, as this plan's commit
`405c502` (Task 1).

### No-baseline claim, verified rather than asserted

Two commands run against the full repository history, both confirming no `SKILL.md` for this
domain ever existed before Task 1's own commit:

```
/usr/bin/git log --all --follow --oneline -- skills/ai-kit-project-rules-arch/SKILL.md
```
Output: exactly one line, `405c502 feat(12-03): write ai-kit-project-rules-arch SKILL.md and
register it in README` -- Task 1's own commit, and nothing before it.

```
/usr/bin/git log --all --diff-filter=A --name-only --pretty=format:%H -- '**/SKILL.md'
```
(filtered for any added path containing "arch") -- output: exactly `skills/ai-kit-project-rules-arch/SKILL.md`,
added once, by commit `405c502` (this task's own preceding commit). No earlier name for this domain
ever carried a `SKILL.md` either -- the architecture-fitness domain is new content this milestone's
family-split design spec introduces; no pre-split combined skill (traced in Phase 9's and Phase 10's
evidence files) ever covered it.

Re-running the same first command now (after this evidence file's own commit will be added) still
returns only that one commit -- the claim holds at write time and remains checkable by a later
reader.

### Step 1 -- installed rubric, read in full before scoring

`/home/bazzite/.claude/skills/skill-judge/SKILL.md` was read in full before scoring. Its
8-dimension, 120-point rubric is UNCHANGED from what Phase 9's `09-SKILL-JUDGE.md`, Phase 10's
`10-SKILL-JUDGE.md`, and Phase 11's `11-SKILL-JUDGE.md` all recorded: D1 Knowledge Delta (20), D2
Mindset + Appropriate Procedures (15), D3 Anti-Pattern Quality (15), D4 Specification Compliance --
Especially Description (15), D5 Progressive Disclosure (15), D6 Freedom Calibration (15), D7
Pattern Recognition (10), D8 Practical Usability (15). No difference from any prior phase's
recorded rubric to report.

### Step 2 -- packaging precondition, confirmed mechanically

```
basename: ai-kit-project-rules-arch
frontmatter name: ai-kit-project-rules-arch
PACKAGING-MATCH-OK
```

Re-confirming Phases 9, 10 and 11's own finding: the installed rubric has NO dimension that reads
the containing directory at all (D4 checks `name:` format and description quality; nothing in D4
or any other dimension compares `name:` against the parent directory's basename). Stated as a
factual finding, not worked around -- no packaging/naming-consistency dimension score is reported
because the installed skill does not produce one.

### Step 3 -- scored

181 lines, no `references/` directory. Follows the "Tool" pattern (decision structure over the
entrypoint-resolution flow, code examples, low freedom, proportionate to a narrower two-
check-family scope than its siblings) -- the same pattern all three sibling skills follow, sized
smaller because this skill's own scope is smaller (two structural checks plus one correlation
check, versus the siblings' five-plus check families).

## Per-dimension scores

| Dimension | Score | Max | Evidence |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense expert content: the exact arch-test shape rule stated as a rule rather than a literal name, the three real chaining mechanisms (direct/transitive prerequisite, recipe invocation), the AST-only correlation concept (parses vs. imports/executes its own checked subject, not a blanket import scan), all four pinned not-verifiable `reason` tokens with what each means for a reader, the canonical-tool-per-stack table with a concrete non-obvious reason per tool (import-linter's Grimp-based AST-only safety against untrusted code; ArchUnit's "failing named test is a stronger CI signal than a side lint pass" reasoning), and the Rust/Go known-gap statement with its own reasoning (declining a confident wrong answer). No "what is a Makefile" or "what is AST" tutorial content anywhere. Docked 3 points relative to the precommit sibling's 18/20 because this skill's total check surface is narrower (two structural checks plus one correlation, versus the sibling's five distinct check families spanning parity/taxonomy/enable-everything/pairs/ruff-specific rules) -- the knowledge is equally dense per line, but there is less of it in total to earn top marks against the "every paragraph earns its tokens, pure knowledge delta" ceiling. |
| D2 Mindset + Procedures | 9 | 15 | Has domain-specific procedures Claude would not otherwise know (the entrypoint-resolution candidate-list ordering and its honest ImportError note; the three-mechanism union that decides "chained"; the parse-vs-execute correlation concept). Does not have an explicit "before doing X, ask yourself" decision-framework, because -- unlike the precommit sibling's genuine research-now/defer/ask branch point -- this skill has no branch point requiring judgment by design: D-A6's whole point is that this skill's knowledge is entirely hardcoded with no research dispatch, so there is no decision this skill's user needs a framework for. This is an honest reflection of the skill's actual shape rather than an omission to fix; a framework manufactured for a branch point that does not exist would be the kind of padding D1's red flags penalize. Scored in the "has domain procedures but lacks thinking frameworks" band because the dimension's rubric does not have a case for "no framework exists because no decision point exists" -- the lower score is accepted as the accurate mechanical result of scoring an intentionally decision-free skill against a rubric written for a broader case, not concealed or argued away. |
| D3 Anti-Pattern Quality | 13 | 15 | 6 anti-patterns, each with a non-obvious WHY. The strongest is "NEVER read a clean report from this skill as proof the architecture is sound" -- a landmine a user would only learn by being burned by exactly the over-claim this project's PROJECT.md core value forbids, paired directly with the scope-limit section it points back to. The not-verifiable-reason-token anti-pattern ("NEVER... paraphrase them... inventing a fifth or renaming one documents a surface the code does not emit") is similarly earned rather than generic. Docked 2 points relative to the precommit sibling's 14/15 for having one fewer anti-pattern overall and no single entry as concretely "landmine-earned" as the sibling's bare-tool-name-indexing example, which cites an actual double failure mode this project's own implementation work discovered. |
| D4 Specification Compliance (description) | 14 | 15 | Single-skill-scope description -- names only this skill's own subject (`arch-test` target existence, chaining, AST-only-ness) in the words a host routes on, with three concrete example trigger phrases and no sibling-domain bleed. Comprehensive WHAT ("whether it exists, whether it is chained... whether that file is AST-only") and WHEN (three "or when asked" phrasings) with searchable keywords (`arch-test`, Makefile, AST-only, architecturally checks). Docked 1 point relative to a perfect score for being slightly denser as a single run-on sentence rather than the more scannable multi-clause structure of the strongest sibling descriptions. |
| D5 Progressive Disclosure | 13 | 15 | No `references/` directory; the entire document is 181 lines, well under both the 500-line hard cap and the ~300-line Tool-pattern target, and self-contained -- every section a reader needs to operate the skill is inline, with nothing orphaned and nothing that should have been extracted (unlike the precommit sibling's own recorded D5 finding, which flagged its Research Step protocol as extractable; this skill has no equivalent bulky, conditionally-needed block to extract, because it has no Research Step at all). Docked 2 points for the same "no references-directory calibration ceiling" reason both sibling evidence files applied to a self-contained skill under this dimension's scoring band, rather than for any identified structural flaw. |
| D6 Freedom Calibration | 13 | 15 | Low freedom throughout, matching the task's fragility: the entrypoint-resolution candidate list (one wrong byte breaks the import), the two subcommands' exact output-key names (a caller writing to a wrong key crashes), and the four pinned not-verifiable reason tokens (a caller branching on a paraphrased string never matches). No high- or medium-freedom judgment calls exist in this skill's scope for the document to mis-calibrate, since the checks themselves are deterministic. Consistent with all three sibling skills' own calibration. |
| D7 Pattern Recognition | 8 | 10 | Clear "Tool" pattern: the entrypoint-resolution flow reads as a decision structure (try each candidate, stop and report if none resolve), working code examples (the Bash candidate loop, the `check`/`remediate` invocations, the worked `remediate` JSON contrasting an auto-applying entry against an advisory one), low freedom throughout. 181 lines is proportionate for this skill's narrower two-structural-check-plus-one-correlation scope, smaller than the ~300-line target in the same direction the family's own scope difference would predict, not as an unexplained deviation. |
| D8 Practical Usability | 13 | 15 | Working code examples throughout (the entrypoint-resolution Bash loop, the two-subcommand invocation lines, the trimmed `remediate` JSON contrasting `auto_apply: true` against `auto_apply: false`), explicit error handling (stop-and-report when no entrypoint candidate resolves), and edge cases covered as first-class content rather than an afterthought -- the four pinned not-verifiable `reason` tokens ARE this skill's edge-case-handling documentation, each with what it means for a reader deciding what to do next. Docked 2 points for omitting a worked JSON example of `check`'s own output shape (only `remediate`'s is shown), a minor but real usability gap for a reader who calls `check` alone and has to infer the shape from prose rather than see it demonstrated. |
| **Total** | **100** | **120** | Grade: 100/120 = 83.3% = B. |

## Findings against `skills/ai-kit-project-rules-arch/SKILL.md`

**No Critical or Important findings.** The two dimensions scoring furthest below their ceiling
(D2 at 9/15, D8 at 13/15) reflect real, but non-blocking, characteristics of this specific skill --
D2's score reflects an honest absence of a decision-framework need (this skill genuinely has no
branch point, by design, D-A6), not a hidden judgment call the document fails to guide; D8's
2-point deduction is a real but Minor gap (no worked `check`-output example) that does not affect
correctness, does not misdocument the code's real behavior, and does not weaken any of the
family-wide scope-boundary, finding-category, or limits content. Because the score (100/120)
already clears the 96/120 alternative pass bar with room to spare, and because Critical/Important
count is zero either way, **no fix-loop iteration was needed (0 of the 3-iteration cap used)**.

The fix loop's four binding constraints (Task 1's verify chain must still pass; the documented
output shapes must still match the code; the three limits statements must survive; the
two-subcommand statement must survive) were therefore never exercised in this task, since no fix
was made. All were re-confirmed unchanged after this review -- see the Acceptance Criteria re-runs
below.

### Acceptance criteria re-runs (Task 1's verify chain, re-confirmed after this review)

- `SKILL-SHAPE-OK` -- re-run verbatim: prints `SKILL-SHAPE-OK ai-kit-project-rules-arch 537` and
  exits 0 (unchanged from Task 1).
- `DOC-MATCHES-CODE-OK` -- re-run verbatim: prints `DOC-MATCHES-CODE-OK ['arch', 'blocked',
  'remediate']` and exits 0 (unchanged from Task 1).
- `TWO-SUBCOMMANDS-OK` -- re-run verbatim: prints `TWO-SUBCOMMANDS-OK` and exits 0 (unchanged from
  Task 1).
- The three limits statements (the four pinned AST-only not-verifiable reason tokens with their
  meanings; the hardcoded no-staleness canonical-tool baseline with the Rust/Go known gap; the
  form-only wiring-vs-architecture scope statement) were re-read in the committed document (`##
  Limits`, lines 128-158) and confirmed present, unmodified, and each still actionable -- no
  judge-driven pressure to remove or dilute any of them arose during scoring, since none was
  identified as a finding.
- The two-subcommand statement (`## Run the check`, lines 82-89: "This skill has exactly two
  subcommands... no `classify` subcommand and no `cache-update` subcommand...") was re-read and
  confirmed present, unmodified, and still explains the difference from the Phase 10/11 siblings by
  name -- no judge-driven pressure to remove it arose during scoring.

## Code-review pointer (for this phase's CODE REVIEW gate)

If the phase's code-review step changes `skills/ai-kit-project-rules-arch/SKILL.md` at all,
`/skill-judge` MUST be re-run against the changed file and THIS file (`12-SKILL-JUDGE.md`) updated
in the same commit, and Task 1's `SKILL-SHAPE-OK`/`DOC-MATCHES-CODE-OK`/`TWO-SUBCOMMANDS-OK` verify
chain MUST be re-run against the changed file. Otherwise, code review should confirm byte-identity
with the file this task scored via:

```
/usr/bin/git diff --quiet 405c50258cff848b6f835492dc7a88504fa82602 -- skills/ai-kit-project-rules-arch/SKILL.md
```

- Evidence file: `.planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-SKILL-JUDGE.md`
- `JUDGED_PATH`: `skills/ai-kit-project-rules-arch/SKILL.md`
- `JUDGED_COMMIT`: `405c50258cff848b6f835492dc7a88504fa82602`
- Score: 100/120, 0 Critical, 0 Important, 0/3 fix iterations used.
