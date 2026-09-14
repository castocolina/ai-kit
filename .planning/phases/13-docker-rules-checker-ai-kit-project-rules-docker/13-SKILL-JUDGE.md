# 13-04 Task 2: `/skill-judge` evidence

Date: 2026-09-14

JUDGED_PATH: skills/ai-kit-project-rules-docker/SKILL.md
JUDGED_COMMIT: df6bbf0b3cb244fa969016ee81b386673f4b5cc5
BASELINE: none (new skill, no prior SKILL.md -- verified by history search, see below)
SCORE: 103/120
CRITICAL: 0
IMPORTANT: 0
FIX_ITERATIONS_USED: 0/3

## Method

This is a brand-new skill: no `SKILL.md` existed for `ai-kit-project-rules-docker` before Task 1
of this plan wrote one. There is nothing to regress against. No synthetic baseline was
constructed, no sibling skill's score (`ai-kit-project-rules-arch` 100/120,
`ai-kit-project-rules-precommit` 103/120, `ai-kit-project-rules-makefile` 103/120,
`ai-kit-project-rules-agents` 102/120) is reused as a stand-in, and the design spec's own
historical figures for a different skill are not cited as if they applied here. The pass bar is
therefore absolute rather than comparative: zero Critical and zero Important findings, or a score
of at least 96/120.

Performed by this executor, running the installed `/skill-judge` skill's rubric, against
`skills/ai-kit-project-rules-docker/SKILL.md` at its committed path, as this plan's commit
`df6bbf0` (Task 1).

### No-baseline claim, verified rather than asserted

Two commands run against the full repository history, both confirming no `SKILL.md` for this
domain ever existed before Task 1's own commit:

```
/usr/bin/git log --all --follow --oneline -- skills/ai-kit-project-rules-docker/SKILL.md
```
Output: exactly one line, `df6bbf0 feat(13-04): write SKILL.md for ai-kit-project-rules-docker
and register in README` -- Task 1's own commit, and nothing before it.

```
/usr/bin/git log --all --diff-filter=A --name-only --pretty=format:%H -- '**/SKILL.md'
```
(filtered for any added path containing "docker") -- output: exactly
`skills/ai-kit-project-rules-docker/SKILL.md`, added once, by commit `df6bbf0` (this task's own
preceding commit). No earlier name for this domain ever carried a `SKILL.md` either -- the Docker
local-dev-convention domain is new content this milestone's family-split design spec introduces;
no pre-split combined skill (traced in Phase 9's, Phase 10's, Phase 11's and Phase 12's evidence
files) ever covered it.

Re-running the same first command now (after this evidence file's own commit will be added) still
returns only that one commit -- the claim holds at write time and remains checkable by a later
reader.

### Step 1 -- installed rubric, read in full before scoring

`/home/bazzite/.claude/skills/skill-judge/SKILL.md` was read in full before scoring. Its
8-dimension, 120-point rubric is UNCHANGED from what Phase 9's `09-SKILL-JUDGE.md`, Phase 10's
`10-SKILL-JUDGE.md`, Phase 11's `11-SKILL-JUDGE.md`, and Phase 12's `12-SKILL-JUDGE.md` all
recorded: D1 Knowledge Delta (20), D2 Mindset + Appropriate Procedures (15), D3 Anti-Pattern
Quality (15), D4 Specification Compliance -- Especially Description (15), D5 Progressive
Disclosure (15), D6 Freedom Calibration (15), D7 Pattern Recognition (10), D8 Practical Usability
(15). No difference from any prior phase's recorded rubric to report.

### Step 2 -- packaging precondition, confirmed mechanically

```
basename: ai-kit-project-rules-docker
frontmatter name: ai-kit-project-rules-docker
PACKAGING-MATCH-OK
```

Re-confirming Phases 9, 10, 11 and 12's own finding: the installed rubric has NO dimension that
reads the containing directory at all (D4 checks `name:` format and description quality; nothing
in D4 or any other dimension compares `name:` against the parent directory's basename). Stated as
a factual finding, not worked around -- no packaging/naming-consistency dimension score is
reported because the installed skill does not produce one.

### Step 3 -- scored

251 lines, no `references/` directory. Follows the "Tool" pattern (decision structure over the
applicability gate and the five finding categories, worked code examples, low freedom), sized
between the Phase 12 sibling's 181 lines (a narrower two-check-family scope) and the Phase 10/11
siblings' larger documents (which also carry a Research Step this skill deliberately lacks) -- the
251-line total sits close to the Tool pattern's own ~300-line target, proportionate to this
skill's five distinct finding categories (one more than the Phase 12 sibling's three).

## Per-dimension scores

| Dimension | Score | Max | Evidence |
|---|---|---|---|
| D1 Knowledge Delta | 18 | 20 | Dense expert content across five check families: the exact eight-name target family with its normalization rule (casefold + `_`->`-`, never a shape rule -- contrasted explicitly against the sibling's own shape-rule approach); the three healthcheck bounds with the non-obvious "strictly greater than, not at-or-above" comparison and the DECLARED-values-only scope (an absent `interval` inherits Compose's own 30s default and is silently NOT flagged -- exactly the kind of Compose-semantics trap only someone who has read the Compose spec closely would know to call out); the four-outcome `depends_on` evaluation, including the non-obvious fact that Compose's OWN implicit default condition is `service_started` (so a bare mapping entry with no `condition:` key is not a neutral omission, it is the form real repos most often write); the three-outcome, five-reason hot-reload check with the REPO-WIDE-not-per-service stack-attribution caveat and the concrete polyglot failure mode it causes; and the flow-mapping/mapping-style parser-scope limits stated as reader contracts rather than bugs. No "what is Docker" or "what is a healthcheck" tutorial content anywhere. Docked 2 points relative to a perfect score because the "Resolve the entrypoint" and "Run the check"/JSON-shape sections repeat a boilerplate pattern shared verbatim in structure (not content) across all five sibling skills' `SKILL.md` files -- Expert content for a first-time reader of the family, but Activation-tier for a reader who has already read a sibling. |
| D2 Mindset + Procedures | 9 | 15 | Has domain-specific procedures Claude would not otherwise know (the entrypoint-resolution candidate-list ordering and its honest `ImportError` note; the fixed five-reason hot-reload evaluation order implied by "advisory naming one of five reasons"; the "what a user does with the output" section's criticality-ordered read-and-confirm procedure). Does not have an explicit "before doing X, ask yourself" decision framework, because -- like the Phase 12 sibling -- this skill has no branch point requiring judgment by design: its whole knowledge surface is hardcoded with no research dispatch (stated explicitly in "Run the check"), so there is no decision this skill's user needs a framework for. This is an honest reflection of the skill's actual shape rather than an omission to fix; inventing a framework for a branch point that does not exist would be the kind of padding D1's red flags penalize. Scored in the same band as the Phase 12 sibling's 9/15 for the same structural reason -- the rubric's scoring bands do not have a case for "no framework exists because no decision point exists," and the lower score is accepted as the accurate mechanical result rather than argued away. |
| D3 Anti-Pattern Quality | 13 | 15 | 7 anti-patterns, each with a non-obvious WHY -- one more than the Phase 12 sibling's 6. The strongest is "NEVER treat an unrecognized hot-reload override as proof a service lacks hot reload," which points directly at the hardcoded-and-staleable marker table (Limits #5) and states the actual consequence of over-trusting it: a false defect claim built on an admittedly incomplete table. "NEVER expect this skill to refactor or rewrite any file it finds a gap in" is earned specifically by contrast with the one sibling skill that DOES have a remediation hand-off, naming the asymmetry rather than asserting a generic report-only rule. Docked 2 points relative to a perfect score for two entries ("NEVER run a container...", "NEVER edit the target repo's...") that restate the family-wide scope boundary already stated in full in the Scope section rather than surfacing a NEW landmine specific to this skill's own domain. |
| D4 Specification Compliance (description) | 14 | 15 | Single-skill-scope description naming only this skill's own subject (the eight-target family, the runbook, the three healthcheck bounds by name, the `depends_on` convention, the hot-reload convention) in the words a host routes on, with three concrete "or when asked" trigger phrasings and no sibling-domain bleed. Comprehensive WHAT (five concrete checks named with their thresholds) and WHEN (three trigger-phrase examples) with searchable keywords (`docker-compose.yml`, healthcheck, `depends_on`, hot-reload, bind mount). Additionally resolves the family's hardest routing ambiguity explicitly -- the one other skill that also has an opinion about a `docker-*`-named target -- naming the split in one clause rather than leaving a host to guess between the two skills on a genuinely overlapping keyword. Docked 1 point relative to a perfect score for being one dense multi-clause sentence rather than the more scannable numbered-list structure the rubric's own "excellent description" example uses. |
| D5 Progressive Disclosure | 13 | 15 | No `references/` directory; the entire document is 251 lines, comfortably under both the 500-line hard cap and the ~300-line Tool-pattern target, and self-contained -- every section a reader needs to operate the skill is inline, with nothing orphaned and nothing that should have been extracted into a reference file (no Research Step block exists to extract, unlike the Phase 10/11 siblings' own recorded D5 findings). Docked 2 points for the same "no references-directory calibration ceiling" reason the Phase 12 sibling's evidence file applied to a self-contained skill under this dimension's scoring band, rather than for any identified structural flaw. |
| D6 Freedom Calibration | 14 | 15 | Low freedom throughout, matching the task's fragility: the entrypoint-resolution candidate list (one wrong byte breaks the import), the exact output-key names for both subcommands, the ten pinned issue-name strings a caller branches on, and the five pinned hot-reload advisory reasons. No high- or medium-freedom judgment call exists in this skill's own scope for the document to mis-calibrate, since every check is deterministic once the compose text is read. Docked 1 point relative to a perfect score because the "What a user does with the output" section leaves "read the remediate list in criticality order" slightly under-specified for the case where two entries share a criticality band -- a minor freedom gap the sibling skills' documents also do not close, but real. |
| D7 Pattern Recognition | 9 | 10 | Clear "Tool" pattern: the applicability-gate decision, the five-category enumeration read as a decision structure over what gets evaluated, working code examples (the entrypoint Bash loop, the two subcommand invocations, the worked `remediate` JSON contrasting an auto-applying entry against an advisory one), low freedom throughout. At 251 lines this sits closer to the Tool pattern's own ~300-line target than the narrower Phase 12 sibling's 181 lines, proportionate to this skill's five-check-family scope (one more finding category than that sibling, plus a longer Limits section covering three checkers' worth of stated gaps rather than one). |
| D8 Practical Usability | 13 | 15 | Working code examples throughout (the entrypoint-resolution Bash loop, the two-subcommand invocation lines, the worked `remediate` JSON contrasting `auto_apply: true` against `auto_apply: false`), explicit degradation behavior (an absent or unreadable Makefile yields all eight target-family findings rather than crashing), and edge cases covered as first-class content -- the eight Limits ARE this skill's edge-case-handling documentation, each stating both which form is unread AND what the user will actually see instead, following the same "say both halves" discipline throughout. Docked 2 points for omitting a worked JSON example of `check`'s own output shape (only `remediate`'s is shown, the same gap the Phase 12 sibling's evidence file recorded) -- a reader who calls `check` alone has to infer the shape from the one-sentence prose description rather than see it demonstrated. |
| **Total** | **103** | **120** | Grade: 103/120 = 85.8% = B. |

## Findings against `skills/ai-kit-project-rules-docker/SKILL.md`

**No Critical or Important findings.** The two dimensions scoring furthest below their ceiling
(D2 at 9/15, D8 at 13/15) reflect real, but non-blocking, characteristics of this specific skill
-- D2's score reflects an honest absence of a decision-framework need (this skill genuinely has no
branch point, by design, matching the Phase 12 sibling's own recorded rationale), not a hidden
judgment call the document fails to guide; D8's 2-point deduction is a real but Minor gap (no
worked `check`-output example) that does not affect correctness, does not misdocument the code's
real behavior, and does not weaken any of the family-wide scope-boundary, finding-category, or
Limits content. Because the score (103/120) already clears the 96/120 alternative pass bar with
room to spare, and because Critical/Important count is zero either way, **no fix-loop iteration
was needed (0 of the 3-iteration cap used)**.

The fix loop's four binding constraints (Task 1's verify chain must still pass; the documented
output shapes must still match the code; every honesty-about-limits statement must survive; the
two-subcommand statement must survive) were therefore never exercised in this task, since no fix
was made. All were re-confirmed unchanged after this review -- see the Acceptance Criteria
re-runs below.

### Acceptance criteria re-runs (Task 1's verify chain, re-confirmed after this review)

- `SKILL-SHAPE-OK` -- re-run verbatim: prints `SKILL-SHAPE-OK ai-kit-project-rules-docker 2338`
  and exits 0 (unchanged from Task 1).
- `DOC-MATCHES-CODE-OK` -- re-run verbatim: prints `DOC-MATCHES-CODE-OK ['docker'] ['blocked',
  'remediate'] 9` and exits 0 (unchanged from Task 1).
- `TWO-SUBCOMMANDS-OK` -- re-run verbatim: prints `TWO-SUBCOMMANDS-OK` and exits 0 (unchanged
  from Task 1).
- `LIMITS-RECONCILED-OK` -- re-run verbatim: prints `LIMITS-RECONCILED-OK eight` and exits 0
  (unchanged from Task 1) -- confirming the conditional seventh limit (13-02's flow-mapping gap)
  is still present alongside the seven required limits, eight total.
- All eight Limits statements (`## Limits`, lines 171-216 of the committed document) were re-read
  and confirmed present, unmodified, and each still actionable as its own standalone sentence --
  no judge-driven pressure to remove or dilute any of them arose during scoring, since none was
  identified as a finding.
- The two-subcommand statement (`## Run the check`, lines 98-105: "This skill has exactly two
  subcommands, `check` and `remediate`... There is no research step and no cache...") was re-read
  and confirmed present, unmodified, and still explains the difference from the Phase 10/11
  siblings by name -- no judge-driven pressure to remove it arose during scoring.

**Necessary-but-not-sufficient axis, stated explicitly (per T-13-26/D-D19):** `SKILL-SHAPE-OK`
and `LIMITS-RECONCILED-OK` are keyword-presence checks -- one token per limit -- and prove only
that a limit was not DELETED, never that its sentence still states something a reader would act
on. Since this task made no edit to any Limits sentence (no fix-loop iteration ran), there is no
before/after wording to compare; the verbatim quotation this control exists to enable is
satisfied trivially here because the text is identical to what Task 1 committed and what this
evidence file already quotes above. `13-04-SUMMARY.md` additionally quotes the full Limits
section verbatim as it stands after this task, per this plan's `<output>` requirement.

## Code-review pointer (for this phase's CODE REVIEW gate)

If the phase's code-review step changes `skills/ai-kit-project-rules-docker/SKILL.md` at all,
`/skill-judge` MUST be re-run against the changed file and THIS file (`13-SKILL-JUDGE.md`)
updated in the same commit, and Task 1's `SKILL-SHAPE-OK`/`DOC-MATCHES-CODE-OK`/
`TWO-SUBCOMMANDS-OK`/`LIMITS-RECONCILED-OK` verify chain MUST be re-run against the changed file.
Otherwise, code review should confirm byte-identity with the file this task scored via:

```
/usr/bin/git diff --quiet df6bbf0b3cb244fa969016ee81b386673f4b5cc5 -- skills/ai-kit-project-rules-docker/SKILL.md
```

- Evidence file: `.planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-SKILL-JUDGE.md`
- `JUDGED_PATH`: `skills/ai-kit-project-rules-docker/SKILL.md`
- `JUDGED_COMMIT`: `df6bbf0b3cb244fa969016ee81b386673f4b5cc5`
- Score: 103/120, 0 Critical, 0 Important, 0/3 fix iterations used.
