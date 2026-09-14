# 11-04 Task 2: `/skill-judge` evidence

Date: 2026-09-14

JUDGED_PATH: skills/ai-kit-project-rules-precommit/SKILL.md
JUDGED_COMMIT: 741fa1b565bc57598e7f759b0de0d97424084d02
BASELINE: none (new skill, no prior SKILL.md -- verified by history search, see below)
SCORE: 103/120
CRITICAL: 0
IMPORTANT: 0
FIX_ITERATIONS_USED: 0/3

## Method

This is a brand-new skill: no `SKILL.md` existed for `ai-kit-project-rules-precommit` before
Task 1 of this plan wrote one. There is nothing to regress against. No synthetic baseline was
constructed, neither sibling skill's score (`ai-kit-project-rules-makefile` 103/120,
`ai-kit-project-rules-agents` 102/120) is reused as a stand-in, and the design spec's own
historical figures for the pre-split `ai-kit-agents-md-rules-checker` skill (98/120 baseline,
~109/120 estimated-after-fixes) are not cited as if they applied here. The pass bar is therefore
absolute rather than comparative: zero Critical and zero Important findings, or a score of at
least 96/120.

Performed by this executor, running the installed `/skill-judge` skill's rubric, against
`skills/ai-kit-project-rules-precommit/SKILL.md` at its committed path, as this plan's commit
`741fa1b` (Task 1).

### No-baseline claim, verified rather than asserted

Two commands run against the full repository history, both confirming no `SKILL.md` for this
domain ever existed before Task 1's own commit:

```
/usr/bin/git log --all --follow --oneline -- skills/ai-kit-project-rules-precommit/SKILL.md
```
Output: exactly one line, `741fa1b feat(11-04): write ai-kit-project-rules-precommit SKILL.md
and register it in README` -- Task 1's own commit, and nothing before it.

```
/usr/bin/git log --all --diff-filter=A --name-only --pretty=format:%H
```
(filtered for any added path whose basename is `SKILL.md` and whose path contains
`precommit`) -- output: exactly `skills/ai-kit-project-rules-precommit/SKILL.md`, added once,
by the same commit. No earlier name for this domain (e.g. a pre-split combined skill covering
pre-commit config) ever carried a `SKILL.md` either -- the pre-split skill's own history (traced
in Phase 9's and Phase 10's evidence files) covered AGENTS.md prose and Makefile shape, never
pre-commit-config parity/taxonomy, which is new domain content introduced by this milestone's
family-split design spec.

Re-running the same first command now (after this evidence file's own commit) still returns only
that one commit -- the claim holds at write time and remains checkable by a later reader.

### Step 1 -- installed rubric, read in full before scoring

`/home/bazzite/.claude/skills/skill-judge/SKILL.md` was read in full before scoring. Its
8-dimension, 120-point rubric is UNCHANGED from what Phase 9's `09-SKILL-JUDGE.md` and Phase 10's
`10-SKILL-JUDGE.md` both recorded: D1 Knowledge Delta (20), D2 Mindset + Appropriate Procedures
(15), D3 Anti-Pattern Quality (15), D4 Specification Compliance -- Especially Description (15),
D5 Progressive Disclosure (15), D6 Freedom Calibration (15), D7 Pattern Recognition (10), D8
Practical Usability (15). No difference from either prior phase's recorded rubric to report.

### Step 2 -- packaging precondition, confirmed mechanically

```
basename: ai-kit-project-rules-precommit
frontmatter name: ai-kit-project-rules-precommit
PACKAGING-MATCH-OK
```

Re-confirming Phase 9's and Phase 10's own finding: the installed rubric has NO dimension that
reads the containing directory at all (D4 checks `name:` format and description quality; nothing
in D4 or any other dimension compares `name:` against the parent directory's basename). Grepping
the full rubric text for "directory"/"packaging"/"consistency" surfaces only D5's mention of a
skill's own `references/` subdirectory, unrelated to packaging/naming. Stated as a factual
finding, not worked around -- no packaging/naming dimension score is reported because the
installed skill does not produce one.

### Step 3 -- scored

246 lines, no `references/` directory. Follows the "Tool" pattern (decision trees, code
examples, low freedom, ~300-line target) -- the same pattern both sibling skills follow.

## Per-dimension scores

| Dimension | Score | Max | Evidence |
|---|---|---|---|
| D1 Knowledge Delta | 18 | 20 | Dense expert content throughout: the exact six-category taxonomy strings, the enable-everything heuristic with its cross-ecosystem reasoning, the duplicate/dead-code most-commonly-skipped heuristic, the confirmed pairs table's existence/role with the closed four-value relationship vocabulary, all three classification confidence levels with a concrete worked asymmetry (bare `ruff` vs `ruff-format`), the presumed-complementary default's reasoning, the nine-of-ten pairs-coverage limit with the rule-family-vs-tool distinction, and the ESLint flat-config-is-a-program limitation. No "what is pre-commit" tutorial content anywhere. The `## Run the check` section's bare CLI invocation lines are low-information but necessary API syntax, not tutorial padding. |
| D2 Mindset + Procedures | 13 | 15 | The "Deciding whether to research now or defer" section is a standalone, context-dependent decision framework (research now / defer / ask when unsure), not a bare choose-one. The Research Step's domain-specific sequence (dispatch sub-task -> scratch file under `./tmp/` -> `cache-update` -> validated write) is a real procedure Claude would not otherwise know, matching the sibling skills' own Research Step shape. |
| D3 Anti-Pattern Quality | 14 | 15 | 7 anti-patterns, each with a non-obvious WHY. The bare-tool-name-indexing anti-pattern is the strongest: it states the CONCRETE double failure mode (misclassifying an already-satisfied hook AND suppressing a real absence finding) that this project's own Phase 11-02 implementation work actually discovered when reasoning about bare `pylint` vs the catalog's `"pylint R0801"` cell -- exactly the kind of landmine-earned specificity D3's scoring criteria reward over a generic warning. |
| D4 Specification Compliance (description) | 13 | 15 | Single-skill-scope description (parity, taxonomy classification, enable-everything, category absence -- all genuinely this one skill's own checks, not bleeding in a sibling's routing surface) with four concrete example trigger phrases and dense keyword coverage (`.pre-commit-config.yaml`, Makefile, parity, all six taxonomy category names, `select = ["ALL"]`, golangci-lint, PMD, ESLint, staticcheck). Docked two points relative to the sibling's 14/15 for length/density: four distinct "when X" clauses chained with "or when Y" make the WHEN slightly less crisp to scan than the makefile sibling's tighter single-paragraph phrasing, even though every clause is genuinely this skill's own scope rather than a neighbouring domain's. |
| D5 Progressive Disclosure | 12 | 15 | The Research Step's full protocol (the value-format/provenance requirement, the worked JSON example, the `cache-update` invocation) is inlined in the main body rather than deferred to a `references/` file loaded on demand -- the same structural characteristic both sibling skills' own evidence files recorded (Phase 9 docked the pre-split baseline to 10/15 for this; Phase 10's makefile skill scored 12/15 for owning the same shape without a sibling to hand it off to). This skill is in the identical position: it genuinely owns this research content now, and the whole document stays well under the 500-line hard cap (246 lines) and close to the Tool pattern's ~300-line target, so the penalty is the same non-blocking size Phase 10's sibling received. The one real, but non-blocking, improvement opportunity this review surfaces -- extracting the Research Step into a conditionally-loaded reference file -- matches the improvement each sibling's own evidence file already named for the identical structural reason. |
| D6 Freedom Calibration | 12 | 15 | Low freedom for the entrypoint-resolution candidate list and the JSON payload shapes (both fragile, one-wrong-byte-costs-an-import or a rejected-write operations); medium freedom for the research-now-vs-defer decision. Consistent with both sibling skills' own calibration. |
| D7 Pattern Recognition | 8 | 10 | Clear "Tool" pattern: decision trees (research now/defer/ask), code examples (entrypoint resolution, JSON worked examples for `remediate`/`classify`/the research findings object), low freedom throughout. 246 lines is proportionate for a single-domain scope carrying five distinct check families (parity, taxonomy, enable-everything, ruff-specific, pairs). |
| D8 Practical Usability | 13 | 15 | Decision framework for the research branch point, working code examples (the entrypoint-resolution Bash loop, the trimmed `remediate` JSON contrasting an auto-applying entry against an advisory one, the `classify` return shape, the research-findings JSON example), explicit error handling (stop-and-report when no entrypoint candidate exists; `cache-update`'s rejection behavior for a bare tool-name guess). |
| **Total** | **103** | **120** | Grade: 103/120 = 85.8% = B. |

## Findings against `skills/ai-kit-project-rules-precommit/SKILL.md`

**No Critical or Important findings.** The one improvement opportunity found (D5: the Research
Step's protocol could move to a `references/` file with an explicit loading trigger) is a
Minor/suggested improvement, not a Critical or Important finding -- it does not affect
correctness, does not misdocument the code's real behavior, and does not weaken any of the
family-wide scope-boundary or anti-pattern content. Because the score (103/120) already clears
the 96/120 alternative pass bar with room to spare, and because Critical/Important count is zero
either way, **no fix-loop iteration was needed (0 of the 3-iteration cap used)**.

The fix loop's three binding constraints (Task 1's verify chain must still pass; the documented
output shapes must still match the code; the three limits statements must survive) were
therefore never exercised in this task, since no fix was made. All three were re-confirmed
unchanged after this review -- see the Acceptance Criteria re-runs below.

### Acceptance criteria re-runs (Task 1's verify chain, re-confirmed after this review)

- `SKILL-SHAPE-OK` -- re-run verbatim: prints `SKILL-SHAPE-OK ai-kit-project-rules-precommit
  828` and exits 0 (unchanged from Task 1).
- `DOC-MATCHES-CODE-OK` -- re-run verbatim: prints `DOC-MATCHES-CODE-OK ['blocked',
  'out_of_taxonomy', 'precommit', 'remediate', 'taxonomy', 'unclassified']` and exits 0
  (unchanged from Task 1).
- The three limits statements (classification confidence, the presumed-complementary default with
  its nine-of-ten sentence, the statically-unreadable-config format) were re-read in the
  committed document (`## Limits`, lines 182-212) and confirmed present, unmodified, and each
  still actionable -- no judge-driven pressure to remove or dilute any of them arose during
  scoring, since none was identified as a finding.

## Code-review pointer (for this phase's CODE REVIEW gate)

If the phase's code-review step changes `skills/ai-kit-project-rules-precommit/SKILL.md` at all,
`/skill-judge` MUST be re-run against the changed file and THIS file (`11-SKILL-JUDGE.md`)
updated in the same commit, and Task 1's `SKILL-SHAPE-OK`/`DOC-MATCHES-CODE-OK` verify chain MUST
be re-run against the changed file. Otherwise, code review should confirm byte-identity with the
file this task scored via:

```
/usr/bin/git diff --quiet 741fa1b565bc57598e7f759b0de0d97424084d02 -- skills/ai-kit-project-rules-precommit/SKILL.md
```

- Evidence file: `.planning/phases/11-pre-commit-rules-checker-ai-kit-project-rules-precommit/11-SKILL-JUDGE.md`
- `JUDGED_PATH`: `skills/ai-kit-project-rules-precommit/SKILL.md`
- `JUDGED_COMMIT`: `741fa1b565bc57598e7f759b0de0d97424084d02`
- Score: 103/120, 0 Critical, 0 Important, 0/3 fix iterations used.
